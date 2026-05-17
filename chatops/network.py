"""
Network device management — SSH/CLI (netmiko) + NETCONF (ncclient).
Supports Cisco IOS, IOS-XE, IOS-XR, NX-OS, VyOS, and generic SSH devices.
"""
import base64
import difflib
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
        if dt == "linux":
            with _netmiko_conn(device) as conn:
                hostname = conn.send_command("hostname", read_timeout=10).strip()
                uname    = conn.send_command("uname -srm", read_timeout=10).strip()
                uptime   = conn.send_command("uptime -p 2>/dev/null || uptime", read_timeout=10).strip()
                os_rel   = conn.send_command("cat /etc/os-release 2>/dev/null", read_timeout=10)
            version = _parse_field(os_rel, r'PRETTY_NAME="(.+?)"', r'VERSION="(.+?)"')
            return {
                "status": "ok", "hostname": hostname, "version": version,
                "uptime": uptime, "model": "Linux Host", "serial": "N/A",
                "raw": uname,
            }
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
            if dt == "linux":
                output = conn.send_command("ip -brief addr show", read_timeout=15)
                ifaces = _parse_linux_interfaces(output)
            elif dt == "cisco_nxos":
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
        dt = device.get("device_type", "cisco_xe")
        if dt == "linux":
            with _netmiko_conn(device) as conn:
                output = conn.send_command("ip route show", read_timeout=15)
            return {"status": "ok", "routes": [], "raw": output[:2000]}
        cmd = f"show ip route vrf {vrf}" if vrf else "show ip route"
        with _netmiko_conn(device) as conn:
            output = conn.send_command(cmd, read_timeout=20)
        routes = _parse_routes(output)
        return {"status": "ok", "routes": routes, "raw": output[:2000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_cpu_memory(device: dict) -> dict:
    """Return CPU and memory utilization."""
    def _to_mb(val: str, unit: str = "bytes") -> str:
        """Normalise a raw numeric string to a human-readable MB/GB value."""
        try:
            n = int(val)
            if unit == "K":
                n *= 1024
            if n >= 1_073_741_824:
                return f"{n / 1_073_741_824:.1f}G"
            return f"{n // 1_048_576}M"
        except Exception:
            return val

    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "linux":
                cpu_out = conn.send_command("top -bn1 | grep -i 'cpu(s)\\|cpu,'", read_timeout=15)
                mem_out = conn.send_command("free -m | grep Mem", read_timeout=10)
                cpu_pct  = _parse_field(cpu_out, r"(\d+\.?\d*)\s*us", r"(\d+\.?\d*)%?\s*user")
                mem_m    = re.search(r"Mem:\s+\d+\s+(\d+)\s+(\d+)", mem_out)
                mem_used = (mem_m.group(1) + "M") if mem_m else "unknown"
                mem_free = (mem_m.group(2) + "M") if mem_m else "unknown"

            elif dt == "cisco_nxos":
                cpu_out = conn.send_command("show processes cpu | grep 'CPU utilization'", read_timeout=15)
                mem_out = conn.send_command("show system resources | grep 'Memory'", read_timeout=15)
                cpu_pct  = _parse_field(cpu_out, r"CPU utilization.*?(\d+\.?\d*)%")
                raw_used = _parse_field(mem_out, r"(\d+)K used")
                raw_free = _parse_field(mem_out, r"(\d+)K free")
                mem_used = _to_mb(raw_used, "K")
                mem_free = _to_mb(raw_free, "K")

            elif dt == "cisco_xr":
                cpu_out = conn.send_command("show processes cpu | include CPU utilization", read_timeout=15)
                mem_out = conn.send_command("show memory summary", read_timeout=15)
                # "CPU utilization for one minute: 1%; five minutes: 1%"
                cpu_pct = _parse_field(cpu_out, r"one minute:\s+(\d+\.?\d*)%",
                                                 r"CPU utilization.*?(\d+\.?\d*)%")
                # "Physical Memory: 4096M total (3584M available)"
                total_m = _parse_field(mem_out, r"Physical Memory:\s+(\d+)M")
                avail_m = _parse_field(mem_out, r"\((\d+)M available\)")
                if total_m != "unknown" and avail_m != "unknown":
                    mem_free = f"{avail_m}M"
                    try:
                        mem_used = f"{int(total_m) - int(avail_m)}M"
                    except Exception:
                        mem_used = "unknown"
                else:
                    mem_used = _parse_field(mem_out, r"Used:\s+(\d+)")
                    mem_free = _parse_field(mem_out, r"Free:\s+(\d+)")

            else:
                # IOS-XE / IOS
                cpu_out = conn.send_command("show processes cpu | include CPU utilization", read_timeout=15)
                mem_out = conn.send_command("show processes memory | include Processor", read_timeout=15)
                cpu_pct  = _parse_field(cpu_out, r"CPU utilization.*?(\d+)%/")
                # IOS-XE 17.x:  "Processor Pool Total: 1090716972 Used: 220888356 Free: 869828616"
                # Older IOS-XE: "Processor  135903000  116940304"
                raw_used = _parse_field(mem_out, r"Used:\s+(\d+)", r"Processor\s+(\d+)\s+\d+")
                raw_free = _parse_field(mem_out, r"Free:\s+(\d+)", r"Processor\s+\d+\s+(\d+)")
                mem_used = _to_mb(raw_used)
                mem_free = _to_mb(raw_free)

        return {
            "status": "ok",
            "cpu_5sec":      cpu_pct,
            "mem_used_bytes": mem_used,
            "mem_free_bytes": mem_free,
            "cpu_raw": cpu_out[:500],
            "mem_raw": mem_out[:500],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_ospf_neighbors(device: dict) -> dict:
    """Return OSPF neighbor summary."""
    try:
        dt = device.get("device_type", "cisco_xe")
        if dt == "linux":
            return {"status": "ok", "neighbors": [], "raw": "N/A — Linux host"}
        with _netmiko_conn(device) as conn:
            if dt == "cisco_nxos":
                output = conn.send_command("show ip ospf neighbors", read_timeout=20)
            elif dt == "cisco_xr":
                output = conn.send_command("show ospf vrf Mgmt-intf neighbor", read_timeout=20)
            else:
                output = conn.send_command("show ip ospf neighbor", read_timeout=20)
        neighbors = _parse_ospf_neighbors(output)
        clean_raw = "\n".join(
            l for l in output.splitlines()
            if "Invalid" not in l and not l.strip().startswith("%") and not re.match(r"^\s*\^\s*$", l)
        )
        return {"status": "ok", "neighbors": neighbors, "raw": clean_raw[:2000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_bgp_neighbors(device: dict) -> dict:
    """Return BGP neighbor summary."""
    try:
        if device.get("device_type") == "linux":
            return {"status": "ok", "neighbors": [], "raw": "N/A — Linux host"}
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "cisco_xr":
                output = conn.send_command("show bgp vrf Mgmt-intf summary", read_timeout=20)
            else:
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


def get_config_diff(device: dict) -> dict:
    """Diff the running-config against the last stored backup."""
    from chatops.db import netdev_get_backup
    dt = device.get("device_type", "cisco_xe")
    if dt == "linux":
        return {"status": "error", "error": "Config diff is not supported for Linux hosts."}
    backup = netdev_get_backup(device["name"])
    if not backup:
        return {"status": "error", "error": "No backup on file. Run a backup first (💾 Backup Config)."}
    try:
        with _netmiko_conn(device) as conn:
            running_raw = conn.send_command("show running-config", read_timeout=60)
    except Exception as e:
        return {"status": "error", "error": str(e)}
    # strip lines that change on every run (timestamps, build info)
    def _clean(text):
        return [l for l in text.splitlines()
                if l.strip()
                and not l.startswith("Building configuration")
                and not re.match(r"^! Last configuration change", l)
                and not re.match(r"^! NVRAM config last", l)]
    running_lines = _clean(running_raw)
    saved_lines   = _clean(backup.get("config_text", ""))
    diff = list(difflib.unified_diff(
        saved_lines, running_lines,
        fromfile=f"backup ({backup.get('backed_up_at','unknown')})",
        tofile="running-config (now)",
        lineterm="", n=3,
    ))
    added   = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
    return {
        "status":    "ok",
        "device":    device["name"],
        "changed":   added + removed > 0,
        "added":     added,
        "removed":   removed,
        "backup_at": backup.get("backed_up_at", "unknown"),
        "diff_lines": diff[:600],
    }


def push_config(device: dict, commands: list) -> dict:
    """Apply a list of config commands in config mode."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "cisco_xr":
                # IOS-XR uses a candidate config model. netmiko's send_config_set
                # exits configure mode with 'end' BEFORE save_config() can commit,
                # so uncommitted changes get discarded. Fix: append 'commit' to the
                # command list so it fires while still inside configure mode.
                output = conn.send_config_set(
                    list(commands) + ["commit"],
                    read_timeout=90,
                )
            else:
                output = conn.send_config_set(commands, read_timeout=30)
                conn.save_config()
        return {"status": "ok", "output": output[:1000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_logs(device: dict, lines: int = 50) -> dict:
    """Return the last N syslog lines from the device."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "linux":
                output = conn.send_command(f"journalctl -n {lines} --no-pager 2>/dev/null || tail -n {lines} /var/log/syslog 2>/dev/null || dmesg | tail -n {lines}", read_timeout=20)
            elif dt == "cisco_nxos":
                output = conn.send_command(f"show logging last {lines}", read_timeout=20)
            elif dt == "cisco_xr":
                output = conn.send_command(f"show logging last {lines}", read_timeout=20)
            else:
                output = conn.send_command(f"show logging | tail count {lines}", read_timeout=20)
                if "Invalid" in output:
                    output = conn.send_command("show logging", read_timeout=20)
                    # Keep only last N non-empty lines
                    kept = [l for l in output.splitlines() if l.strip()][-lines:]
                    output = "\n".join(kept)
        entries = _parse_log_entries(output, dt)
        return {"status": "ok", "entries": entries, "raw": output[:6000], "lines_requested": lines}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_traceroute(device: dict, target: str, max_ttl: int = 15) -> dict:
    """Run a traceroute from the device to a target."""
    import socket
    try:
        dt = device.get("device_type", "cisco_xe")
        # Resolve hostname to IP server-side — Cisco sandbox routers have no DNS configured
        resolved = target
        if not re.match(r"^[\d\.]+$", target):
            try:
                resolved = socket.gethostbyname(target)
            except socket.gaierror:
                resolved = target  # keep original, let device handle it
        with _netmiko_conn(device) as conn:
            if dt == "linux":
                # -m max hops, -w wait secs, -q 1 probe per hop
                output = conn.send_command(
                    f"traceroute -m {max_ttl} -w 2 -q 1 {resolved}",
                    read_timeout=max_ttl * 4, expect_string=r"\$"
                )
            elif dt == "cisco_xr":
                # ttl 1 N limits max hops; timeout 2, probe 1 keeps it fast
                output = conn.send_command(
                    f"traceroute {resolved} ttl 1 {max_ttl} timeout 2 probe 1",
                    read_timeout=max_ttl * 4, expect_string=r"#"
                )
            elif dt == "cisco_nxos":
                output = conn.send_command(
                    f"traceroute {resolved}",
                    read_timeout=max_ttl * 6, expect_string=r"#"
                )
            else:
                # IOS-XE: ttl 1 N limits max hops; timeout 2, probe 1 keeps it fast
                output = conn.send_command(
                    f"traceroute {resolved} ttl 1 {max_ttl} timeout 2 probe 1",
                    read_timeout=max_ttl * 4, expect_string=r"#"
                )
        resolved_note = f" (resolved from {target})" if resolved != target else ""
        hops = _parse_traceroute(output, dt)
        return {"status": "ok", "target": target, "resolved": resolved + resolved_note, "hops": hops, "raw": output[:3000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def ping_device(device: dict, target: str = "8.8.8.8", count: int = 5) -> dict:
    """Run a ping from the device to a target."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "linux":
                output = conn.send_command(
                    f"ping -c {count} -W 2 {target}",
                    read_timeout=count * 4 + 5, expect_string=r"\$"
                )
                m = re.search(r"(\d+)% packet loss", output)
                success = str(100 - int(m.group(1))) if m else "0"
            elif dt == "cisco_xr":
                # IOS-XR management interface is in Mgmt-intf VRF; global table has no route back.
                # XR ping syntax uses 'repeat' (not 'count' which is NX-OS).
                output = conn.send_command(
                    f"ping vrf Mgmt-intf {target} repeat {count}",
                    read_timeout=count * 4 + 10, expect_string=r"#"
                )
                success = _parse_field(output, r"Success rate is (\d+) percent")
                if success == "unknown":
                    # VRF may not be named Mgmt-intf on this device; fall back to global routing
                    output = conn.send_command(
                        f"ping {target} repeat {count}",
                        read_timeout=count * 4 + 10, expect_string=r"#"
                    )
                    success = _parse_field(output, r"Success rate is (\d+) percent")
            elif dt == "cisco_nxos":
                # NX-OS uses 'count' not 'repeat'; management subnet reachable via management VRF
                output = conn.send_command(
                    f"ping {target} count {count} vrf management",
                    read_timeout=count * 4 + 10, expect_string=r"#"
                )
                m = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
                success = str(int(100 - float(m.group(1)))) if m else _parse_field(output, r"Success rate is (\d+) percent")
            else:
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
        if dt == "linux":
            with _netmiko_conn(device) as conn:
                output = conn.send_command("ip neigh show", read_timeout=15)
            entries = []
            for line in output.splitlines():
                # 10.10.20.254 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
                m = re.match(r"^([\d\.]+)\s+dev\s+(\S+)\s+lladdr\s+([\da-fA-F:]+)", line, re.IGNORECASE)
                if m:
                    entries.append({"ip": m.group(1), "mac": m.group(3), "interface": m.group(2)})
            return {"status": "ok", "entries": entries, "raw": output[:1500]}
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


# ── CDP / LLDP Neighbor Discovery ─────────────────────────────────────────────

def get_cdp_neighbors(device: dict) -> dict:
    """Return CDP neighbor list; falls back to LLDP if CDP is disabled."""
    try:
        dt = device.get("device_type", "cisco_xe")
        if dt == "linux":
            return {"status": "ok", "neighbors": [], "raw": "N/A — Linux host"}
        with _netmiko_conn(device) as conn:
            output = conn.send_command("show cdp neighbors detail", read_timeout=20)
            if "CDP is not enabled" in output or "% Invalid" in output:
                output = conn.send_command("show lldp neighbors detail", read_timeout=20)
        neighbors = _parse_cdp_neighbors(output)
        clean_raw = "\n".join(
            l for l in output.splitlines()
            if "Invalid" not in l and not l.strip().startswith("%")
            and not re.match(r"^\s*\^\s*$", l)
        )
        return {"status": "ok", "neighbors": neighbors, "raw": clean_raw[:3000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Interface Error Counters ───────────────────────────────────────────────────

def get_interface_errors(device: dict) -> dict:
    """Return per-interface error counters (input errors, CRC, output errors, drops, resets)."""
    try:
        dt = device.get("device_type", "cisco_xe")
        with _netmiko_conn(device) as conn:
            if dt == "linux":
                output = conn.send_command("ip -s link show", read_timeout=20)
            elif dt == "cisco_nxos":
                output = conn.send_command("show interface", read_timeout=30)
            else:
                output = conn.send_command("show interfaces", read_timeout=30)
        interfaces = _parse_interface_errors(output, dt)
        return {"status": "ok", "interfaces": interfaces, "raw": output[:5000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── MAC Address Table ──────────────────────────────────────────────────────────

def get_mac_table(device: dict) -> dict:
    """Return MAC address table (IOS-XE and NX-OS only; routers return N/A)."""
    try:
        dt = device.get("device_type", "cisco_xe")
        if dt == "cisco_xr":
            return {"status": "ok", "entries": [], "raw": "N/A — IOS-XR is a router, no L2 MAC table"}
        if dt == "linux":
            return {"status": "ok", "entries": [], "raw": "N/A — Linux host"}
        with _netmiko_conn(device) as conn:
            output = conn.send_command("show mac address-table", read_timeout=20)
        entries = _parse_mac_table(output, dt)
        clean_raw = "\n".join(
            l for l in output.splitlines()
            if not l.strip().startswith("%") and not re.match(r"^\s*\^\s*$", l)
        )
        return {"status": "ok", "entries": entries, "raw": clean_raw[:3000]}
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

def _re_int(pattern: str, text: str) -> int:
    """Return first integer capture group matched by pattern, or 0."""
    m = re.search(pattern, text)
    if not m:
        return 0
    for g in m.groups():
        if g is not None:
            try:
                return int(g)
            except (ValueError, TypeError):
                pass
    return 0


def _parse_cdp_neighbors(text: str) -> list:
    """Parse 'show cdp neighbors detail' output for IOS-XE, IOS-XR, and NX-OS."""
    neighbors = []
    blocks = re.split(r'\n-{5,}', text)
    for block in blocks:
        m_dev = re.search(r'Device ID[:\s]+(\S+)', block)
        if not m_dev:
            continue
        m_ip   = re.search(r'(?:IP address|IPv4 Address)[:\s]+([\d.]+)', block, re.I)
        m_plat = re.search(r'Platform:\s*(.+?),', block)
        m_if   = re.search(r'Interface:\s*(\S+),\s*Port ID.*?:\s*(\S+)', block)
        m_cap  = re.search(r'Capabilities:\s*(.+)', block)
        neighbors.append({
            "device_id":       m_dev.group(1).strip(),
            "ip":              m_ip.group(1) if m_ip else "—",
            "platform":        m_plat.group(1).strip() if m_plat else "—",
            "local_interface": m_if.group(1) if m_if else "—",
            "remote_port":     m_if.group(2) if m_if else "—",
            "capabilities":    m_cap.group(1).strip() if m_cap else "—",
        })
    return neighbors


def _parse_interface_errors(text: str, dt: str) -> list:
    """Parse error counters from show interfaces / show interface / ip -s link."""
    results = []

    if dt == "linux":
        iface = rx_err = rx_drop = tx_err = tx_drop = 0
        cur = None
        in_rx = in_tx = False
        for line in text.splitlines():
            m = re.match(r'^\d+:\s+(\S+?):', line)
            if m:
                if cur:
                    results.append({"interface": cur, "input_errors": rx_err, "crc": 0,
                                    "output_errors": tx_err, "input_drops": rx_drop,
                                    "output_drops": tx_drop, "resets": 0,
                                    "has_errors": any(x > 0 for x in [rx_err, rx_drop, tx_err, tx_drop])})
                cur, rx_err, rx_drop, tx_err, tx_drop = m.group(1), 0, 0, 0, 0
                in_rx = in_tx = False
            elif 'RX:' in line:
                in_rx, in_tx = True, False
            elif 'TX:' in line:
                in_tx, in_rx = True, False
            elif in_rx:
                p = line.split()
                if len(p) >= 4 and p[2].isdigit():
                    rx_err, rx_drop = int(p[2]), int(p[3])
                in_rx = False
            elif in_tx:
                p = line.split()
                if len(p) >= 4 and p[2].isdigit():
                    tx_err, tx_drop = int(p[2]), int(p[3])
                in_tx = False
        if cur:
            results.append({"interface": cur, "input_errors": rx_err, "crc": 0,
                            "output_errors": tx_err, "input_drops": rx_drop,
                            "output_drops": tx_drop, "resets": 0,
                            "has_errors": any(x > 0 for x in [rx_err, rx_drop, tx_err, tx_drop])})
        return results

    if dt == "cisco_nxos":
        blocks = re.split(r'\n(?=\S+\s+is\s+(?:up|down))', text)
        for block in blocks:
            m = re.match(r'^(\S+)\s+is\s+(up|down)', block, re.I)
            if not m:
                continue
            ie = _re_int(r'(\d+)\s+input error', block)
            crc = _re_int(r'(\d+)\s+CRC', block)
            oe = _re_int(r'(\d+)\s+output errors', block)
            idrop = _re_int(r'(\d+)\s+input discard', block)
            odrop = _re_int(r'(\d+)\s+output discard', block)
            results.append({"interface": m.group(1), "input_errors": ie, "crc": crc,
                            "output_errors": oe, "input_drops": idrop, "output_drops": odrop,
                            "resets": 0, "has_errors": any(x > 0 for x in [ie, crc, oe, idrop, odrop])})
        return results

    # IOS-XE / IOS-XR: blocks start at non-indented lines
    blocks = re.split(r'\n(?=\S)', text)
    for block in blocks:
        m = re.match(r'^(\S+)\s+is\s+(up|down|admin)', block, re.I)
        if not m:
            continue
        ie    = _re_int(r'(\d+)\s+input errors', block)
        crc   = _re_int(r'(\d+)\s+CRC', block)
        oe    = _re_int(r'(\d+)\s+output errors', block)
        rst   = _re_int(r'(\d+)\s+interface resets', block)
        odrop = _re_int(r'[Tt]otal output drops[:\s]+(\d+)|(\d+)\s+output drops', block)
        idrop = _re_int(r'[Tt]otal input drops[:\s]+(\d+)|(\d+)\s+input drops', block)
        results.append({"interface": m.group(1), "input_errors": ie, "crc": crc,
                        "output_errors": oe, "input_drops": idrop, "output_drops": odrop,
                        "resets": rst, "has_errors": any(x > 0 for x in [ie, crc, oe, rst, odrop])})
    return results


def _parse_mac_table(text: str, dt: str) -> list:
    """Parse MAC address table from IOS-XE or NX-OS output."""
    entries = []
    for line in text.splitlines():
        if dt == "cisco_nxos":
            m = re.match(r'[*+CGO~]?\s*(\d+)\s+([\da-fA-F.:]+)\s+(\S+)\s+\d+\s+[TF]\s+[TF]\s+(\S+)', line)
        else:
            m = re.match(r'^\s*(\d+)\s+([\da-fA-F.]+)\s+(\S+)\s+(\S+)', line)
        if m:
            entries.append({"vlan": m.group(1), "mac": m.group(2),
                            "type": m.group(3).lower(), "port": m.group(4)})
    return entries


def _parse_field(text: str, *patterns) -> str:
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "unknown"


def _parse_linux_interfaces(text: str) -> list:
    """Parse 'ip -brief addr show' output.
    Format: lo  UNKNOWN  127.0.0.1/8  / eth0  UP  10.10.20.50/24
    """
    ifaces = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name  = parts[0]
        state = parts[1].lower()   # UP, DOWN, UNKNOWN
        ips   = [p.split("/")[0] for p in parts[2:] if re.match(r"[\d\.]+/\d+", p)]
        ip    = ips[0] if ips else "unassigned"
        ifaces.append({
            "interface": name,
            "ip":        ip,
            "status":    "up" if state in ("up", "unknown") else "down",
            "protocol":  state,
            "in_rate":   None, "out_rate":  None,
            "errors_in": None, "errors_out": None,
        })
    return ifaces


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


def _parse_ospf_neighbors(text: str) -> list:
    """Parse OSPF neighbor table from IOS-XE, IOS-XR, and NX-OS output.

    Common format across all platforms:
      Neighbor ID  Pri  State         Dead Time  Address       Interface
      10.10.20.35    1  FULL/DR       00:00:38   10.10.20.35   Gi1
    """
    neighbors = []
    for line in text.splitlines():
        # Match lines starting with an IP (neighbor ID)
        m = re.match(
            r"^\s*([\d\.]+)\s+(\d+)\s+(\S+)\s+([\d:]+|-+)\s+([\d\.]+)\s+(\S+)",
            line
        )
        if m:
            state_full = m.group(3)          # e.g. FULL/DR, 2WAY/DROTHER
            state_parts = state_full.split("/")
            neighbors.append({
                "neighbor_id": m.group(1),
                "priority":    m.group(2),
                "state":       state_parts[0],   # FULL, 2WAY, INIT, etc.
                "role":        state_parts[1] if len(state_parts) > 1 else "—",
                "dead_time":   m.group(4),
                "address":     m.group(5),
                "interface":   m.group(6),
            })
    return neighbors


def _parse_log_entries(text: str, dt: str) -> list:
    """Parse syslog lines into structured entries with severity, timestamp, message."""
    severity_map = {
        "EMERG": 0, "ALERT": 1, "CRIT": 2, "CRITICAL": 2,
        "ERR": 3, "ERROR": 3, "WARN": 4, "WARNING": 4,
        "NOTICE": 5, "INFO": 6, "DEBUG": 7,
    }
    entries = []
    for line in text.splitlines():
        if not line.strip():
            continue
        # Cisco syslog: *Mar  1 00:00:01.123: %LINEPROTO-5-UPDOWN: ...
        m = re.match(r"^[*.]?(\w+\s+\d+\s+[\d:\.]+):\s+%(\w+)-(\d)-(\w+):\s*(.+)", line)
        if m:
            sev_num = int(m.group(3))
            sev_label = ["EMERG","ALERT","CRIT","ERR","WARN","NOTICE","INFO","DEBUG"][min(sev_num, 7)]
            entries.append({
                "timestamp": m.group(1).strip(),
                "facility":  m.group(2),
                "severity":  sev_num,
                "severity_label": sev_label,
                "mnemonic":  m.group(4),
                "message":   m.group(5).strip(),
            })
            continue
        # IOS-XR / NX-OS timestamp format: 2024-01-15 10:23:45 or RP/0/...
        m2 = re.match(r"^([\d\-]+ [\d:]+\.\d+)\s+(\S+)\s+%(\w+)-(\d)-(\w+):\s*(.+)", line)
        if m2:
            sev_num = int(m2.group(4))
            sev_label = ["EMERG","ALERT","CRIT","ERR","WARN","NOTICE","INFO","DEBUG"][min(sev_num, 7)]
            entries.append({
                "timestamp": m2.group(1),
                "facility":  m2.group(3),
                "severity":  sev_num,
                "severity_label": sev_label,
                "mnemonic":  m2.group(5),
                "message":   m2.group(6).strip(),
            })
            continue
        # Linux syslog / journalctl: Jan 15 10:23:45 host process[pid]: message
        m3 = re.match(r"^(\w{3}\s+\d+\s+[\d:]+)\s+(\S+)\s+(\S+?)(?:\[\d+\])?:\s*(.+)", line)
        if m3:
            msg = m3.group(4)
            sev = 6  # INFO default
            for kw, num in [("error", 3), ("err:", 3), ("warn", 4), ("crit", 2), ("fail", 3)]:
                if kw in msg.lower():
                    sev = num
                    break
            entries.append({
                "timestamp": m3.group(1),
                "facility":  m3.group(3),
                "severity":  sev,
                "severity_label": ["EMERG","ALERT","CRIT","ERR","WARN","NOTICE","INFO","DEBUG"][sev],
                "mnemonic":  "",
                "message":   msg.strip(),
            })
    return entries


def _parse_traceroute(text: str, dt: str) -> list:
    """Parse traceroute output into hop list."""
    hops = []
    for line in text.splitlines():
        # Cisco: " 1  10.10.20.254  4 msec  4 msec  4 msec"
        m = re.match(r"^\s*(\d+)\s+([\d\.]+|\*)\s+([\d\.\*]+\s*msec.*)", line)
        if m:
            rtt_raw = m.group(3)
            rtts = re.findall(r"(\d+)\s*msec", rtt_raw)
            avg = round(sum(int(r) for r in rtts) / len(rtts)) if rtts else None
            hops.append({"hop": int(m.group(1)), "ip": m.group(2), "rtt_ms": avg, "rtt_raw": rtt_raw.strip()})
            continue
        # Linux traceroute: " 1  gateway (192.168.1.1)  1.234 ms  1.111 ms  1.089 ms"
        m2 = re.match(r"^\s*(\d+)\s+\S+\s+\(([\d\.]+)\)\s+([\d\.\s msa*]+)", line)
        if not m2:
            m2 = re.match(r"^\s*(\d+)\s+([\d\.]+|\*)\s+(.*)", line)
        if m2:
            rtt_raw = m2.group(3)
            rtts = re.findall(r"([\d\.]+)\s*ms", rtt_raw)
            avg = round(sum(float(r) for r in rtts) / len(rtts)) if rtts else None
            hops.append({"hop": int(m2.group(1)), "ip": m2.group(2), "rtt_ms": avg, "rtt_raw": rtt_raw.strip()})
    return hops
