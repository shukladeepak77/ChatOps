"""
Network device management — SSH/CLI (netmiko) + NETCONF (ncclient).
Supports Cisco IOS, IOS-XE, IOS-XR, NX-OS, VyOS, and generic SSH devices.
"""
import base64
import re
import xml.etree.ElementTree as ET
from typing import Optional



# ── Credential helpers ────────────────────────────────────────────────────────

def encode_password(pw: str) -> str:
    """Obfuscate password for storage — use a secret manager in production."""
    return base64.b64encode(pw.encode()).decode()


def decode_password(enc: str) -> str:
    try:
        return base64.b64decode(enc.encode()).decode()
    except Exception:
        return enc


# ── Connection helpers ────────────────────────────────────────────────────────

def _netmiko_conn(device: dict):
    from netmiko import ConnectHandler
    import paramiko
    # Re-enable ssh-dss (DSA) and ssh-rsa for legacy IOS-XR devices.
    # IOS-XRv 9K only offers ssh-dss host key — disabled in modern paramiko/OpenSSH.
    try:
        preferred = list(paramiko.Transport._preferred_keys)
        for alg in ("ssh-dss", "ssh-rsa"):
            if alg not in preferred:
                preferred.append(alg)
        paramiko.Transport._preferred_keys = preferred
    except Exception:
        pass
    pw = decode_password(device.get("password_enc", ""))
    return ConnectHandler(
        device_type=device.get("device_type", "cisco_xe"),
        host=device["host"],
        port=int(device.get("port", 22)),
        username=device["username"],
        password=pw,
        timeout=15,
        session_timeout=20,
        conn_timeout=10,
        fast_cli=False,
    )


def _ncclient_conn(device: dict):
    from ncclient import manager
    pw = decode_password(device.get("password_enc", ""))
    return manager.connect(
        host=device["host"],
        port=int(device.get("netconf_port", 830)),
        username=device["username"],
        password=pw,
        hostkey_verify=False,
        timeout=20,
        device_params={"name": _netconf_device_type(device.get("device_type", "cisco_xe"))},
    )


def _netconf_device_type(dt: str) -> str:
    mapping = {
        "cisco_xe":    "iosxe",
        "cisco_ios":   "ios",
        "cisco_xr":    "iosxr",
        "cisco_nxos":  "nexus",
        "juniper":     "junos",
        "default":     "default",
    }
    return mapping.get(dt, "default")


# ── SSH/CLI operations ────────────────────────────────────────────────────────

def get_device_info(device: dict) -> dict:
    """Return hostname, version, uptime via 'show version'."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            output = conn.send_command("show version", read_timeout=20)
        if dt == "cisco_nxos":
            hostname = _parse_field(output, r"Device name:\s+(\S+)")
            version  = _parse_field(output, r"NXOS:\s+version\s+([\d\.\(\)a-zA-Z]+)",
                                            r"system:\s+version\s+([\d\.\(\)a-zA-Z]+)")
            uptime   = _parse_field(output, r"Kernel uptime is\s+(.+)")
            model    = _parse_field(output, r"cisco\s+(Nexus[\w\s]+Series)",
                                            r"Hardware\s*\n\s+cisco\s+(\S+)")
            serial   = _parse_field(output, r"Processor Board ID\s+(\S+)")
        else:
            hostname = _parse_field(output, r"^(\S+)\s+uptime", r"hostname\s+(\S+)")
            version  = _parse_field(output, r"Version\s+([\d\w\.\(\)]+)")
            uptime   = _parse_field(output, r"uptime is\s+(.+)")
            model    = _parse_field(output, r"[Cc]isco\s+([\w\-]+)\s+.*[Pp]rocessor",
                                            r"Hardware:\s+\S+,\s+(\S+)")
            serial   = _parse_field(output, r"[Ss]erial [Nn]umber\s*:\s*(\S+)",
                                            r"System serial number\s*:\s*(\S+)")
        return {
            "status": "ok", "hostname": hostname, "version": version,
            "uptime": uptime, "model": model, "serial": serial,
            "raw": output[:800],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_interfaces(device: dict) -> dict:
    """Return interface list with status, IP, speed."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "cisco_nxos":
                brief = conn.send_command("show interface status", read_timeout=20)
                mgmt_ip = conn.send_command("show ip interface brief vrf management", read_timeout=15)
                ifaces = _parse_nxos_interface_status(brief, mgmt_ip)
            elif dt == "cisco_xr":
                brief = conn.send_command("show ip interface brief", read_timeout=20)
                ifaces = _parse_xr_ip_int_brief(brief)
            else:
                brief = conn.send_command("show ip interface brief", read_timeout=20)
                stats = conn.send_command("show interfaces", read_timeout=30)
                ifaces = _parse_ip_int_brief(brief)
                _enrich_with_stats(ifaces, stats)
        return {"status": "ok", "interfaces": ifaces}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_routes(device: dict, vrf: str = None) -> dict:
    """Return IP routing table."""
    try:
        cmd = f"show ip route vrf {vrf}" if vrf else "show ip route"
        with _netmiko_conn(device) as conn:
            output = conn.send_command(cmd, read_timeout=20)
        routes = _parse_routes(output)
        return {"status": "ok", "routes": routes, "raw": output[:2000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_cpu_memory(device: dict) -> dict:
    """Return CPU and memory utilization."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "cisco_nxos":
                cpu_out = conn.send_command("show processes cpu | grep 'CPU utilization'", read_timeout=15)
                mem_out = conn.send_command("show system resources | grep 'Memory'", read_timeout=15)
                cpu_pct  = _parse_field(cpu_out, r"CPU utilization.*?(\d+\.?\d*)%")
                mem_used = _parse_field(mem_out, r"(\d+)K used")
                mem_free = _parse_field(mem_out, r"(\d+)K free")
            else:
                cpu_out = conn.send_command("show processes cpu | include CPU utilization", read_timeout=15)
                mem_out = conn.send_command("show processes memory | include Processor", read_timeout=15)
                cpu_pct  = _parse_field(cpu_out, r"CPU utilization.*?(\d+)%/")
                mem_used = _parse_field(mem_out, r"Processor\s+(\d+)\s+\d+")
                mem_free = _parse_field(mem_out, r"Processor\s+\d+\s+(\d+)")
        return {
            "status": "ok",
            "cpu_5sec": cpu_pct,
            "mem_used_bytes": mem_used,
            "mem_free_bytes": mem_free,
            "cpu_raw":  cpu_out[:500],
            "mem_raw":  mem_out[:500],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_bgp_neighbors(device: dict) -> dict:
    """Return BGP neighbor summary."""
    try:
        with _netmiko_conn(device) as conn:
            output = conn.send_command("show bgp summary", read_timeout=20)
            if "Invalid" in output or "not active" in output.lower():
                output = conn.send_command("show ip bgp summary", read_timeout=20)
        neighbors = _parse_bgp_summary(output)
        clean_raw = "\n".join(
            l for l in output.splitlines()
            if "Invalid" not in l and not l.strip().startswith("%") and not re.match(r"^\s*\^\s*$", l)
        )
        return {"status": "ok", "neighbors": neighbors, "raw": clean_raw[:1500]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def backup_config(device: dict) -> dict:
    """Pull the running configuration."""
    try:
        with _netmiko_conn(device) as conn:
            config = conn.send_command("show running-config", read_timeout=60)
        lines = [l for l in config.splitlines() if l.strip() and not l.startswith("Building")]
        return {"status": "ok", "config": "\n".join(lines), "lines": len(lines)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def push_config(device: dict, commands: list) -> dict:
    """Apply a list of config commands in config mode."""
    try:
        with _netmiko_conn(device) as conn:
            output = conn.send_config_set(commands, read_timeout=30)
            conn.save_config()
        return {"status": "ok", "output": output[:1000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def ping_device(device: dict, target: str = "8.8.8.8", count: int = 5) -> dict:
    """Run a ping from the device to a target."""
    try:
        with _netmiko_conn(device) as conn:
            output = conn.send_command(
                f"ping {target} repeat {count}", read_timeout=30, expect_string=r"#"
            )
        success = _parse_field(output, r"Success rate is (\d+) percent")
        return {"status": "ok", "target": target, "success_rate": success, "raw": output[:400]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_arp_table(device: dict) -> dict:
    """Return ARP table entries."""
    try:
        dt = device.get("device_type", "cisco_xe")
        cmd = "show ip arp" if dt == "cisco_nxos" else "show arp"
        with _netmiko_conn(device) as conn:
            output = conn.send_command(cmd, read_timeout=20)
        entries = []
        for line in output.splitlines():
            m = re.match(
                r"\S+\s+([\d\.]+)\s+[\d:]+\s+([\da-fA-F.]+)\s+ARPA\s+(\S+)", line
            )
            if m:
                entries.append({"ip": m.group(1), "mac": m.group(2), "interface": m.group(3)})
        return {"status": "ok", "entries": entries, "raw": output[:1500]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── NETCONF operations ────────────────────────────────────────────────────────

def netconf_get_interfaces(device: dict) -> dict:
    """Get interface state via NETCONF (IOS-XE)."""
    filter_xml = """
    <filter>
      <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
    </filter>"""
    try:
        with _ncclient_conn(device) as mgr:
            reply = mgr.get(filter=("subtree", filter_xml))
        root = ET.fromstring(str(reply))
        ns = {"if": "urn:ietf:params:xml:ns:yang:ietf-interfaces"}
        ifaces = []
        for iface in root.iter("{urn:ietf:params:xml:ns:yang:ietf-interfaces}interface"):
            name  = _xml_text(iface, "if:name", ns)
            state = _xml_text(iface, "if:oper-status", ns)
            speed = _xml_text(iface, "if:speed", ns)
            ifaces.append({"name": name, "status": state, "speed": speed})
        return {"status": "ok", "interfaces": ifaces, "protocol": "netconf"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_field(text: str, *patterns) -> str:
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "unknown"


def _parse_xr_ip_int_brief(text: str) -> list:
    """Parse IOS-XR 'show ip interface brief' — columns: Interface IP Status Protocol VRF."""
    ifaces = []
    for line in text.splitlines():
        # Skip header/timestamp lines
        if re.match(r"^\s*(Interface|RP/|Mon|Tue|Wed|Thu|Fri|Sat|Sun|\s*$)", line):
            continue
        m = re.match(r"^(\S+)\s+([\d\.]+|unassigned)\s+(\S+)\s+(\S+)", line)
        if m:
            ifaces.append({
                "interface": m.group(1),
                "ip":        m.group(2),
                "status":    m.group(3).lower(),
                "protocol":  m.group(4).lower(),
                "in_rate": None, "out_rate": None,
                "errors_in": None, "errors_out": None,
            })
    return ifaces


def _parse_nxos_interface_status(text: str, mgmt_ip_text: str = "") -> list:
    """Parse NX-OS 'show interface status'.
    Shows all physical ports regardless of L3 configuration.
    Format: Port  [Name]  Status  Vlan  Duplex  Speed  Type
    mgmt_ip_text: output of 'show ip interface brief vrf management' to resolve mgmt0 IP.
    """
    status_map = {
        "connected": "up", "notconnect": "down", "disabled": "down",
        "err-disabled": "down", "sfpAbsent": "down", "xcvrAbsent": "down",
        "noOperMembers": "down",
    }
    # Extract mgmt0 IP from management VRF output
    mgmt_ip = "unassigned"
    for line in mgmt_ip_text.splitlines():
        m = re.match(r"^mgmt\d+\s+([\d\.]+)", line)
        if m:
            mgmt_ip = m.group(1)
            break

    ifaces = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        port = parts[0]
        if not re.match(r"^(mgmt|Eth|Lo|Vlan|port-channel|Po)", port):
            continue
        # Scan parts for a known status keyword — handles optional Name column
        for p in parts[1:]:
            if p in status_map:
                ip = mgmt_ip if port.startswith("mgmt") else "unassigned"
                ifaces.append({
                    "interface": port,
                    "ip":        ip,
                    "status":    status_map[p],
                    "protocol":  p,
                    "in_rate":   None,
                    "out_rate":  None,
                    "errors_in": None,
                    "errors_out": None,
                })
                break
    return ifaces


def _parse_ip_int_brief(text: str) -> list:
    ifaces = []
    for line in text.splitlines():
        m = re.match(
            r"^(\S+)\s+([\d\.]+|unassigned)\s+\S+\s+\S+\s+(\S+)\s+(\S+)", line
        )
        if m:
            ifaces.append({
                "interface": m.group(1),
                "ip":        m.group(2),
                "status":    m.group(3),
                "protocol":  m.group(4),
                "in_rate":   None,
                "out_rate":  None,
                "errors_in": None,
                "errors_out": None,
            })
    return ifaces


def _enrich_with_stats(ifaces: list, stats_text: str) -> None:
    blocks = re.split(r"(?=^\S)", stats_text, flags=re.MULTILINE)
    stats_map = {}
    for block in blocks:
        name_m = re.match(r"^(\S+) is", block)
        if not name_m:
            continue
        name = name_m.group(1)
        in_r  = re.search(r"input rate (\d+) bits", block)
        out_r = re.search(r"output rate (\d+) bits", block)
        in_e  = re.search(r"(\d+) input errors", block)
        out_e = re.search(r"(\d+) output errors", block)
        stats_map[name] = {
            "in_rate":    int(in_r.group(1))  if in_r  else 0,
            "out_rate":   int(out_r.group(1)) if out_r else 0,
            "errors_in":  int(in_e.group(1))  if in_e  else 0,
            "errors_out": int(out_e.group(1)) if out_e else 0,
        }
    for iface in ifaces:
        s = stats_map.get(iface["interface"])
        if s:
            iface.update(s)


def _parse_routes(text: str) -> list:
    routes = []
    for line in text.splitlines():
        m = re.match(
            r"^([A-Z*>i][\w\s]*?)\s+([\d\.]+/\d+)\s+\[(\d+)/(\d+)\] via ([\d\.]+)", line
        )
        if m:
            routes.append({
                "code":     m.group(1).strip(),
                "network":  m.group(2),
                "distance": m.group(3),
                "metric":   m.group(4),
                "next_hop": m.group(5),
            })
    return routes


def _parse_bgp_summary(text: str) -> list:
    neighbors = []
    in_table = False
    for line in text.splitlines():
        if re.match(r"Neighbor\s+V\s+AS", line):
            in_table = True
            continue
        if in_table and re.match(r"[\d\.]+", line.strip()):
            parts = line.split()
            if len(parts) >= 9:
                neighbors.append({
                    "neighbor": parts[0],
                    "as":       parts[2],
                    "state":    parts[8] if not parts[8].isdigit() else "Established",
                    "prefixes": parts[8] if parts[8].isdigit() else "0",
                    "updown":   parts[7],
                })
    return neighbors


def _xml_text(element, tag: str, ns: dict) -> str:
    el = element.find(tag, ns)
    return el.text.strip() if el is not None and el.text else ""
