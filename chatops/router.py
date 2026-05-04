import re
import subprocess as _subprocess
from typing import Dict

from rapidfuzz import fuzz, process as rfuzz_process

from .actions import (
    check_disk,
    check_memory,
    check_cpu,
    check_processes,
    check_uptime,
    check_ports,
    check_ip,
    check_routes,
    check_network_stats,
    check_dns,
    check_connections,
    check_service,
    check_failed_services,
    analyze_logs as analyze_logs_action,
    help_text as help_text_action,
    alert_status,
    run_tests,
    copy_ssh_key,
)
from .config import load_config
from .runbooks import list_runbooks, request_runbook, confirm_runbook, cancel_runbook

# Intent keyword map — order matters: more specific phrases listed first
_INTENTS: Dict[str, list] = {
    "logs":        ["analyze logs", "log analysis", "check logs", "analyze log", "parse logs"],
    "processes":   ["top processes", "running processes", "process list", "what is running", "show processes", "ps aux", "processes", "process"],
    "ports":       ["open ports", "listening ports", "check ports", "network ports", "show ports"],
    "health":      ["system health", "system status", "system overview", "overall health", "how is system"],
    "runbooks":    ["list runbooks", "available runbooks", "show runbooks", "what runbooks"],
    "alerts":      ["show alerts", "recent alerts", "alert history", "view alerts", "list alerts"],
    "disk":        ["disk", "storage", "space", "filesystem", "drive", "how full", "disk usage"],
    "memory":      ["memory", "ram", "mem", "swap", "how much memory", "how much ram"],
    "cpu":         ["cpu", "processor", "cpu usage", "cpu load", "compute"],
    "uptime":      ["uptime", "up time", "how long", "server uptime", "been up", "running since"],
    "config":      ["config", "configuration", "settings", "thresholds", "show system config", "system config"],
    "help":        ["help", "commands", "what can you do", "options"],
    "ip":          ["check ip", "ip address", "show ip", "interfaces", "ip addr"],
    "routes":      ["check routes", "routing table", "ip route", "show routes"],
    "network":     ["check network", "network stats", "network traffic", "interface stats"],
    "dns":         ["check dns", "dns lookup", "dns check", "name resolution"],
    "connections": ["check connections", "active connections", "tcp connections"],
    "service":     ["service status", "check service"],
    "failed":      ["check failed services", "failed services", "systemctl failed"],
    "nodes":       ["list nodes", "show nodes", "nodes"],
}

_ALL_PHRASES = [
    (phrase, intent)
    for intent, phrases in _INTENTS.items()
    for phrase in phrases
]

_pending_restart: str | None = None
_pending_ssh_copy: str | None = None


def _detect_intent(s: str) -> str:
    # Exact substring match first (faster and more reliable)
    for intent, keywords in _INTENTS.items():
        if any(kw in s for kw in keywords):
            return intent
    # Fuzzy fallback
    phrases = [p for p, _ in _ALL_PHRASES]
    result = rfuzz_process.extractOne(s, phrases, scorer=fuzz.WRatio, score_cutoff=72)
    if result:
        matched = result[0]
        for phrase, intent in _ALL_PHRASES:
            if phrase == matched:
                return intent
    return "unknown"


def route_message(message: str) -> Dict[str, str]:
    global _pending_restart, _pending_ssh_copy
    raw = (message or "").strip()
    raw_lower = raw.lower()
    # Allow - for node/service names
    s = re.sub(r"[^a-z0-9\s:_\-]", "", raw_lower).strip()

    cfg = load_config()

    # ── Node management (parsed from raw_lower to preserve @ and .) ───────────
    add_node_m = re.match(
        r'^add\s+node\s+(\S+)\s+([\w.\-]+@[\w.\-]+)(?:\s+(\S+))?', raw_lower
    )
    if add_node_m:
        from .nodes import add_node as _add_node
        name = add_node_m.group(1)
        user_host = add_node_m.group(2)
        key = add_node_m.group(3) or "~/.ssh/id_rsa"
        user, host = user_host.split("@", 1)
        _add_node(name, host, user, key)
        return {"response": f"Node '{name}' added — {user}@{host}  (key: {key})"}

    rm_node_m = re.match(r'^remove\s+node\s+(\S+)$', s)
    if rm_node_m:
        from .nodes import remove_node as _remove_node
        name = rm_node_m.group(1)
        if _remove_node(name):
            return {"response": f"Node '{name}' removed."}
        return {"response": f"Node '{name}' not found."}

    if s in ("list nodes", "show nodes", "nodes"):
        from .nodes import list_nodes as _list_nodes
        nodes = _list_nodes()
        if not nodes:
            return {"response": "No nodes registered.\nUsage: add node <name> <user>@<host> [key_path]"}
        lines = ["Registered nodes:"]
        for n, info in nodes.items():
            lines.append(f"  {n} — {info['user']}@{info['host']}  (key: {info['key_path']})")
        return {"response": "\n".join(lines)}

    # ── "on <node>" / "on all" suffix ─────────────────────────────────────────
    on_match = re.search(r'\s+on\s+(all|[\w\-]+)$', s)
    target_node = None
    if on_match:
        target_node = on_match.group(1)
        s = s[:on_match.start()].strip()

    # ── Special prefix commands ────────────────────────────────────────────────
    if not s or s == "help":
        return {"response": help_text_action()}

    if re.match(r"^run\s+tests?(\s+suite)?$", s) or s in ("pytest", "test suite", "run test cases", "run chatops tests", "run test suite"):
        return run_tests()

    # Inline log analysis
    log_match = re.match(r"^(?:analyze\s+logs?|check\s+logs?)\s*:?\s+(.+)$", s, re.DOTALL)
    if log_match:
        logs = log_match.group(1).strip()
        placeholder = re.sub(r'\s+', ' ', logs).lower()
        if placeholder in ("<paste log content here>", "paste log content here", "<content>", "content"):
            return {"response": "Usage: analyze logs: <paste log content here>\nYou can also upload a log file using the Upload Log button."}
        data = analyze_logs_action(logs)
        actions = ", ".join(data.get("suggested_actions", []))
        return {
            "response": (
                f"Log Analysis → Severity: {data['severity']} | "
                f"Root cause: {data['root_cause']} | "
                f"Impact: {data['impact']} | "
                f"Actions: {actions}"
            )
        }

    # ── Service commands ───────────────────────────────────────────────────────
    svc_status_m = re.match(r'^service\s+status\s+([\w\-]+)$', s)
    if svc_status_m:
        name = svc_status_m.group(1)
        d = check_service(name)
        pid_info = f"  PID: {d['pid']}" if d.get("pid") and d["pid"] != "0" else ""
        desc = f"  {d['description']}" if d.get("description") else ""
        lines = [
            f"Service: {name}",
            f"  Status: {d['state']} ({d.get('sub_state', '')})",
        ]
        if pid_info:
            lines.append(pid_info)
        if desc:
            lines.append(desc)
        return {"response": "\n".join(lines)}

    restart_m = re.match(r'^restart\s+([\w\-]+)$', s)
    if restart_m:
        name = restart_m.group(1)
        _pending_restart = name
        ssh_warning = (
            "\n\n⚠️  WARNING: Restarting SSH will drop your current SSH session.\n"
            "   Tip: run 'systemctl restart ssh &' in a terminal to stay connected."
        ) if name in ("ssh", "sshd") else ""
        return {
            "response": (
                f"Restart service '{name}'?\n"
                f"Command: systemctl restart {name}"
                f"{ssh_warning}\n\n"
                f"Reply 'confirm restart {name}' to proceed, or 'cancel' to abort."
            )
        }

    confirm_restart_m = re.match(r'^confirm\s+restart\s+([\w\-]+)$', s)
    if confirm_restart_m:
        name = confirm_restart_m.group(1)
        if _pending_restart != name:
            return {"response": f"No pending restart for '{name}'. Use 'restart {name}' first."}
        _pending_restart = None
        result = _subprocess.run(
            ["systemctl", "restart", name], capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return {"response": f"Service '{name}' restarted successfully."}
        return {"response": f"Failed to restart '{name}': {result.stderr.strip() or 'permission denied or service not found'}"}

    if s in ("check failed services", "failed services"):
        failed = check_failed_services()
        if not failed:
            return {"response": "No failed services detected."}
        return {"response": "Failed services:\n" + "\n".join(f"  {f}" for f in failed)}

    # copy ssh key <user@host>
    ssh_copy_m = re.match(r'^copy\s+ssh\s+key\s+(\S+@\S+)$', raw_lower)
    if ssh_copy_m:
        target = ssh_copy_m.group(1)
        _pending_ssh_copy = target
        return {
            "response": (
                f"Copy SSH public key to '{target}'?\n"
                f"This will run: ssh-copy-id -i ~/.ssh/id_rsa.pub {target}\n"
                f"(Key will be auto-generated if it does not exist.)\n\n"
                f"Reply 'confirm copy ssh key' to proceed, or 'cancel' to abort."
            )
        }

    if s == "confirm copy ssh key":
        if not _pending_ssh_copy:
            return {"response": "No pending SSH key copy. Use 'copy ssh key user@host' first."}
        target = _pending_ssh_copy
        _pending_ssh_copy = None
        result = copy_ssh_key(target)
        if result["status"] == "ok":
            return {"response": result["message"]}
        return {"response": f"SSH key copy failed:\n{result['message']}"}

    # Runbook: run <name>
    run_match = re.match(r"^run\s+([\w\-]+)", s)
    if run_match:
        result = request_runbook(run_match.group(1))
        return {"response": result["message"]}

    confirm_match = re.match(r"^confirm\s+([\w\-]+)", s)
    if confirm_match:
        result = confirm_runbook(confirm_match.group(1))
        if result["status"] == "ok":
            return {"response": f"Runbook executed.\n\n{result.get('output', '')}"}
        return {"response": result.get("message", "Error.")}

    if s == "cancel":
        _pending_restart = None
        _pending_ssh_copy = None
        result = cancel_runbook()
        return {"response": result["message"]}

    # config set slack_webhook <url>  — match case-insensitively but preserve original URL case
    slack_cfg_m = re.match(r'^config\s+set\s+slack[-_]?webhook\s+(\S+)$', raw, re.IGNORECASE)
    if slack_cfg_m:
        from .config import save_config as _save_config
        url = slack_cfg_m.group(1)
        _save_config({"slack_webhook": url})
        return {"response": f"Slack webhook configured. CRITICAL alerts will be sent to Slack."}

    suppress_m = re.match(r'^config\s+set\s+alert\s+suppress\s+(\d+)$', s)
    if suppress_m:
        from .config import save_config as _save_config
        minutes = int(suppress_m.group(1))
        _save_config({"alert_suppress_minutes": minutes})
        return {"response": f"Alert suppression set to {minutes} minutes."}

    if s == "test slack":
        from .config import load_config as _load_config
        from .actions import notify_slack as _notify_slack
        import socket
        cfg_ts = _load_config()
        webhook = cfg_ts.get("slack_webhook", "").strip()
        if not webhook:
            return {"response": "No Slack webhook configured. Use: config set slack_webhook <url>"}
        ok, err = _notify_slack(webhook, "test", "TEST", 0.0, socket.gethostname())
        if ok:
            return {"response": "Test notification sent to Slack."}
        return {"response": f"Failed to send — {err or 'check the webhook URL.'}"}

    # show report [Nh]
    report_m = re.match(r'^show\s+report(?:\s+(\d+)h?)?$', s)
    if report_m:
        from .actions import generate_report, format_report_text
        hours = int(report_m.group(1)) if report_m.group(1) else 24
        report = generate_report(hours)
        return {"response": format_report_text(report)}

    # config set report hour <N>
    report_hour_m = re.match(r'^config\s+set\s+report\s+hour\s+(\d+)$', s)
    if report_hour_m:
        from .config import save_config as _save_config
        hour = max(0, min(23, int(report_hour_m.group(1))))
        _save_config({"report_hour": hour, "report_enabled": True})
        return {"response": f"Daily report enabled and scheduled for {hour:02d}:00 each day."}

    # config set report on/off
    report_toggle_m = re.match(r'^config\s+set\s+report\s+(on|off|enable|disable)$', s)
    if report_toggle_m:
        from .config import save_config as _save_config
        enabled = report_toggle_m.group(1) in ("on", "enable")
        _save_config({"report_enabled": enabled})
        status = "enabled" if enabled else "disabled"
        return {"response": f"Daily report {status}."}

    # ── Intent detection ───────────────────────────────────────────────────────
    intent = _detect_intent(s)

    # ── Intents handled locally even when a node is specified ─────────────────
    if intent == "alerts":
        from .db import get_alerts, unacked_count
        node_filter = target_node if target_node and target_node != "all" else None
        alerts = get_alerts(limit=5, node=node_filter)
        count = unacked_count(node=node_filter)
        scope = f" for [{node_filter}]" if node_filter else ""
        if not alerts:
            return {"response": f"No alerts recorded{scope} yet."}
        lines = [f"Recent alerts{scope} ({count} unacknowledged):"]
        for a in alerts:
            ack = "✓" if a["acked"] else "!"
            lines.append(f"  [{ack}] [{a['severity']}] {a['message']}  ({a['timestamp']})")
        return {"response": "\n".join(lines)}

    # ── Remote dispatch ────────────────────────────────────────────────────────
    if target_node:
        return _route_remote(intent, target_node, s)

    # ── Local intent routing ───────────────────────────────────────────────────
    if intent == "disk":
        data = check_disk()
        status = alert_status(data["percent_used"], cfg["disk_warning"], cfg["disk_critical"])
        return {
            "response": (
                f"Disk: {data['percent_used']:.1f}% used "
                f"({data['used_gb']:.1f} GB / {data['total_gb']:.1f} GB free: {data['free_gb']:.1f} GB) — {status}"
            ),
        }

    if intent == "memory":
        data = check_memory()
        status = alert_status(data["percent_used"], cfg["memory_warning"], cfg["memory_critical"])
        return {
            "response": (
                f"Memory: {data['percent_used']:.1f}% used "
                f"({data['used_mb']:,} MB / {data['total_mb']:,} MB) — {status}"
            ),
        }

    if intent == "cpu":
        data = check_cpu()
        status = alert_status(data["percent_used"], cfg["cpu_warning"], cfg["cpu_critical"])
        return {
            "response": (
                f"CPU: {data['percent_used']:.1f}% used "
                f"({data['cpu_count']} logical cores) — {status}"
            ),
        }

    if intent == "uptime":
        data = check_uptime()
        uptime_str = f"{data['uptime_days']}d {data['uptime_hours']}h {data['uptime_minutes']}m"
        return {"response": f"Uptime: {uptime_str}"}

    if intent == "ports":
        data = check_ports()
        ports = ", ".join(str(p["port"]) for p in data) if data else "none found"
        return {"response": f"Open ports: {ports}"}

    if intent == "processes":
        procs = check_processes(5)
        if not procs:
            return {"response": "Could not retrieve process list."}
        lines = ["Top 5 processes by CPU:"]
        for p in procs:
            lines.append(f"  [{p['pid']}] {p['name']} — CPU {p['cpu_pct']}% | MEM {p['mem_pct']}%")
        return {"response": "\n".join(lines)}

    if intent == "health":
        disk = check_disk()
        mem = check_memory()
        cpu = check_cpu()
        up = check_uptime()
        disk_st = alert_status(disk["percent_used"], cfg["disk_warning"], cfg["disk_critical"])
        mem_st  = alert_status(mem["percent_used"],  cfg["memory_warning"], cfg["memory_critical"])
        cpu_st  = alert_status(cpu["percent_used"],  cfg["cpu_warning"], cfg["cpu_critical"])
        statuses = [disk_st, mem_st, cpu_st]
        overall = "CRITICAL" if "CRITICAL" in statuses else ("WARNING" if "WARNING" in statuses else "OK")
        uptime_str = f"{up['uptime_days']}d {up['uptime_hours']}h {up['uptime_minutes']}m"
        return {
            "response": (
                f"System Health — Overall: {overall}\n"
                f"  Disk:   {disk_st} ({disk['percent_used']:.1f}%)\n"
                f"  Memory: {mem_st} ({mem['percent_used']:.1f}%)\n"
                f"  CPU:    {cpu_st} ({cpu['percent_used']:.1f}%)\n"
                f"  Uptime: {uptime_str}"
            ),
            "overall_status": overall,
            "disk_status":    disk_st,
            "memory_status":  mem_st,
            "cpu_status":     cpu_st,
            "uptime":         uptime_str,
        }


    if intent == "runbooks":
        rbs = list_runbooks()
        lines = ["Available runbooks:"]
        for rb in rbs:
            lines.append(f"  run {rb['name']} — {rb['description']}")
        return {"response": "\n".join(lines)}

    if intent == "config":
        webhook = cfg.get("slack_webhook", "")
        webhook_display = webhook if webhook else "(not configured)"
        report_status = "Enabled" if cfg.get("report_enabled") else "Disabled"
        lines = [
            "System Configuration",
            "",
            "Disk Thresholds:",
            f"  Warning:   {cfg.get('disk_warning')}%",
            f"  Critical:  {cfg.get('disk_critical')}%",
            "",
            "Memory Thresholds:",
            f"  Warning:   {cfg.get('memory_warning')}%",
            f"  Critical:  {cfg.get('memory_critical')}%",
            "",
            "CPU Thresholds:",
            f"  Warning:   {cfg.get('cpu_warning')}%",
            f"  Critical:  {cfg.get('cpu_critical')}%",
            "",
            "Health Check:",
            f"  Interval:  {cfg.get('health_check_interval')}s",
            "",
            "Slack:",
            f"  Webhook:   {webhook_display}",
            f"  Suppress:  {cfg.get('alert_suppress_minutes')} minutes",
            "",
            "Daily Report:",
            f"  Status:    {report_status}",
            f"  Hour:      {cfg.get('report_hour', 8):02d}:00",
        ]
        return {"response": "\n".join(lines)}

    if intent == "logs":
        return {"response": "Usage: analyze logs: <paste log content here>"}

    if intent == "help":
        return {"response": help_text_action()}

    # ── Network intents ────────────────────────────────────────────────────────
    if intent == "ip":
        ifaces = check_ip()
        if not ifaces:
            return {"response": "Could not retrieve IP addresses."}
        lines = ["Network interfaces:"]
        for i in ifaces:
            addrs = "  ".join(i["addresses"]) if i["addresses"] else "no address"
            lines.append(f"  {i['interface']:<12} {i['state']:<10} {addrs}")
        return {"response": "\n".join(lines)}

    if intent == "routes":
        routes = check_routes()
        if not routes:
            return {"response": "Could not retrieve routing table."}
        cols = ["Destination", "Gateway", "Interface", "Proto", "Src", "Metric"]
        keys = ["destination", "gateway", "interface", "proto", "src", "metric"]
        widths = [max(len(c), max(len(r[k]) for r in routes)) for c, k in zip(cols, keys)]
        def _row(vals):
            return "  " + "  ".join(v.ljust(w) for v, w in zip(vals, widths))
        header = _row(cols)
        sep = "  " + "  ".join("-" * w for w in widths)
        rows = [_row([r[k] for k in keys]) for r in routes]
        return {"response": "Routing table:\n" + header + "\n" + sep + "\n" + "\n".join(rows)}

    if intent == "network":
        stats = check_network_stats()
        if not stats:
            return {"response": "Could not retrieve network stats."}
        lines = ["Network interface stats:"]
        for s_item in stats:
            lines.append(f"  {s_item['interface']}")
            lines.append(
                f"    RX: {s_item['bytes_recv_mb']:.1f} MB  "
                f"({s_item['pkts_recv']:,} pkts)  "
                f"Err: {s_item['errors_in']}  Drop: {s_item['drops_in']}"
            )
            lines.append(
                f"    TX: {s_item['bytes_sent_mb']:.1f} MB  "
                f"({s_item['pkts_sent']:,} pkts)  "
                f"Err: {s_item['errors_out']}  Drop: {s_item['drops_out']}"
            )
        return {"response": "\n".join(lines)}

    if intent == "dns":
        dns_results = check_dns()
        lines = ["DNS resolution check:"]
        for r in dns_results:
            if r["status"] == "OK":
                lines.append(f"  {r['hostname']} → {r['resolved_ip']}  Latency: {r['latency_ms']}ms  OK")
            else:
                lines.append(f"  {r['hostname']} → {r['status']}")
        return {"response": "\n".join(lines)}

    if intent == "connections":
        conn = check_connections()
        by_state = "  ".join(f"{k}: {v}" for k, v in conn["by_state"].items())
        return {"response": f"TCP connections: {conn['total']} total  ({by_state or 'none'})"}

    if intent == "service":
        return {"response": "Usage: service status <name>"}

    if intent == "failed":
        failed = check_failed_services()
        if not failed:
            return {"response": "No failed services detected."}
        return {"response": "Failed services:\n" + "\n".join(f"  {f}" for f in failed)}

    if intent == "nodes":
        from .nodes import list_nodes as _list_nodes
        nodes = _list_nodes()
        if not nodes:
            return {"response": "No nodes registered.\nUsage: add node <name> <user>@<host> [key_path]"}
        lines = ["Registered nodes:"]
        for n, info in nodes.items():
            lines.append(f"  {n} — {info['user']}@{info['host']}  (key: {info['key_path']})")
        return {"response": "\n".join(lines)}

    return {
        "response": (
            "I didn't understand that. Try: check disk, check memory, check cpu, "
            "check ip, service status <name>, or type 'help' for all commands."
        )
    }


def _annotate_status(output: str, intent: str, cfg: dict) -> str:
    """Append — STATUS to remote output lines that carry a percentage."""
    if output.startswith("Error") or output.startswith("Connection"):
        return output
    if intent == "disk":
        m = re.search(r"Disk:\s+([\d.]+)%", output)
        if m:
            st = alert_status(float(m.group(1)), cfg["disk_warning"], cfg["disk_critical"])
            return output + f"  — {st}"
    elif intent == "memory":
        m = re.search(r"Memory:\s+([\d.]+)%", output)
        if m:
            st = alert_status(float(m.group(1)), cfg["memory_warning"], cfg["memory_critical"])
            return output + f"  — {st}"
    elif intent == "health":
        disk_m = re.search(r"Disk:\s+([\d.]+)%", output)
        mem_m  = re.search(r"Memory:\s+([\d.]+)%", output)
        cpu_m  = re.search(r"CPU:\s+([\d.]+)%", output)
        if disk_m and mem_m:
            dst = alert_status(float(disk_m.group(1)), cfg["disk_warning"], cfg["disk_critical"])
            mst = alert_status(float(mem_m.group(1)),  cfg["memory_warning"], cfg["memory_critical"])
            cst = alert_status(float(cpu_m.group(1)),  cfg["cpu_warning"], cfg["cpu_critical"]) if cpu_m else "OK"
            statuses = [dst, mst, cst]
            overall = "CRITICAL" if "CRITICAL" in statuses else ("WARNING" if "WARNING" in statuses else "OK")
            output = re.sub(r"Disk:\s+([\d.]+)%",   lambda m: f"Disk:   {dst} ({m.group(1)}%)", output)
            output = re.sub(r"Memory:\s+([\d.]+)%", lambda m: f"Memory: {mst} ({m.group(1)}%)", output)
            if cpu_m:
                output = re.sub(r"CPU:\s+([\d.]+)%", lambda m: f"CPU:    {cst} ({m.group(1)}%)", output)
            output = f"Overall: {overall}\n" + output
    return output


def _run_local_intent(intent: str, cfg: dict) -> str:
    """Run an intent locally and return plain text output (used for localhost node in 'on all')."""
    try:
        if intent == "disk":
            d = check_disk()
            st = alert_status(d["percent_used"], cfg["disk_warning"], cfg["disk_critical"])
            return f"Disk: {d['percent_used']:.1f}%  [{st}]"
        if intent == "memory":
            m = check_memory()
            st = alert_status(m["percent_used"], cfg["memory_warning"], cfg["memory_critical"])
            return f"Memory: {m['percent_used']:.1f}%  [{st}]"
        if intent == "cpu":
            c = check_cpu()
            st = alert_status(c["percent_used"], cfg["cpu_warning"], cfg["cpu_critical"])
            return f"CPU: {c['percent_used']:.1f}%  [{st}]"
        if intent == "uptime":
            u = check_uptime()
            return f"up {u['uptime_days']}d {u['uptime_hours']}h {u['uptime_minutes']}m"
        if intent == "health":
            disk = check_disk(); mem = check_memory(); cpu = check_cpu(); up = check_uptime()
            dst = alert_status(disk["percent_used"], cfg["disk_warning"], cfg["disk_critical"])
            mst = alert_status(mem["percent_used"],  cfg["memory_warning"], cfg["memory_critical"])
            cst = alert_status(cpu["percent_used"],  cfg["cpu_warning"], cfg["cpu_critical"])
            overall = "CRITICAL" if "CRITICAL" in (dst, mst, cst) else ("WARNING" if "WARNING" in (dst, mst, cst) else "OK")
            return (f"Overall: {overall}\n"
                    f"Disk:   {dst} ({disk['percent_used']:.1f}%)\n"
                    f"Memory: {mst} ({mem['percent_used']:.1f}%)\n"
                    f"CPU:    {cst} ({cpu['percent_used']:.1f}%)\n"
                    f"Uptime: {up['uptime_days']}d {up['uptime_hours']}h {up['uptime_minutes']}m")
    except Exception as e:
        return f"Error: {e}"
    return "(not supported locally)"


def _route_remote(intent: str, target: str, raw_cmd: str) -> Dict[str, str]:
    from .nodes import list_nodes as _list_nodes
    from .ssh import run_remote, REMOTE_CMDS

    all_nodes = _list_nodes()
    cfg = load_config()

    if not all_nodes:
        return {"response": "No nodes registered. Use: add node <name> <user>@<host>"}

    if intent not in REMOTE_CMDS:
        return {"response": f"Command '{raw_cmd}' is not supported for remote execution."}

    if target == "all":
        lines = [f"Remote: {raw_cmd} — all nodes\n"]
        for name, node in all_nodes.items():
            if node.get("host") in ("127.0.0.1", "localhost"):
                output = _run_local_intent(intent, cfg)
                lines.append(f"[{name}]  local")
            else:
                output = _annotate_status(run_remote(node, REMOTE_CMDS[intent]), intent, cfg)
                lines.append(f"[{name}]  {node['user']}@{node['host']}")
            for line in output.splitlines():
                lines.append(f"  {line}")
            lines.append("")
        return {"response": "\n".join(lines).rstrip()}

    node = all_nodes.get(target)
    if not node:
        available = ", ".join(all_nodes.keys())
        return {"response": f"Unknown node '{target}'. Available: {available}"}

    output = _annotate_status(run_remote(node, REMOTE_CMDS[intent]), intent, cfg)
    lines = [f"[{target}]  {node['user']}@{node['host']}"]
    for line in output.splitlines():
        lines.append(f"  {line}")
    return {"response": "\n".join(lines)}
