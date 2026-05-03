import re
from typing import Dict

from rapidfuzz import fuzz, process as rfuzz_process

from .actions import (
    check_disk,
    check_memory,
    check_cpu,
    check_processes,
    check_uptime,
    check_ports,
    analyze_logs as analyze_logs_action,
    help_text as help_text_action,
    alert_status,
    run_tests,
)
from .config import load_config
from .runbooks import list_runbooks, request_runbook, confirm_runbook, cancel_runbook

# Intent keyword map — order matters: more specific phrases listed first
_INTENTS: Dict[str, list] = {
    "logs":      ["analyze logs", "log analysis", "check logs", "analyze log", "parse logs"],
    "processes": ["top processes", "running processes", "process list", "what is running", "show processes", "ps aux", "processes", "process"],
    "ports":     ["open ports", "listening ports", "check ports", "network ports", "show ports"],
    "health":    ["system health", "system status", "system overview", "overall health", "how is system"],
    "runbooks":  ["list runbooks", "available runbooks", "show runbooks", "what runbooks"],
    "alerts":    ["show alerts", "recent alerts", "alert history", "view alerts", "list alerts"],
    "disk":      ["disk", "storage", "space", "filesystem", "drive", "how full", "disk usage"],
    "memory":    ["memory", "ram", "mem", "swap", "how much memory", "how much ram"],
    "cpu":       ["cpu", "processor", "cpu usage", "cpu load", "compute"],
    "uptime":    ["uptime", "up time", "how long", "server uptime", "been up", "running since"],
    "config":    ["config", "configuration", "settings", "thresholds"],
    "help":      ["help", "commands", "what can you do", "options"],
}

_ALL_PHRASES = [
    (phrase, intent)
    for intent, phrases in _INTENTS.items()
    for phrase in phrases
]


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
    raw = (message or "").strip()
    s = re.sub(r"[^a-z0-9\s:_]", "", raw.lower()).strip()

    # ── Special prefix commands ────────────────────────────────────────────────

    if not s or s == "help":
        return {"response": help_text_action()}

    # Run tests shortcut (must be checked before generic "run <name>" pattern)
    if re.match(r"^run\s+tests?(\s+suite)?$", s) or s in ("pytest", "test suite", "run test cases", "run chatops tests", "run test suite"):
        return run_tests()

    # Inline log analysis: "analyze logs: <content>"
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

    # Runbook: run <name>
    run_match = re.match(r"^run\s+(\S+)", s)
    if run_match:
        result = request_runbook(run_match.group(1))
        return {"response": result["message"]}

    # Runbook: confirm <name>
    confirm_match = re.match(r"^confirm\s+(\S+)", s)
    if confirm_match:
        result = confirm_runbook(confirm_match.group(1))
        if result["status"] == "ok":
            return {"response": f"Runbook executed.\n\n{result.get('output', '')}"}
        return {"response": result["message"]}

    # Runbook: cancel
    if s == "cancel":
        result = cancel_runbook()
        return {"response": result["message"]}

    # ── Intent-based routing ───────────────────────────────────────────────────

    intent = _detect_intent(s)
    cfg = load_config()

    if intent == "disk":
        data = check_disk()
        status = alert_status(data["percent_used"], cfg["disk_warning"], cfg["disk_critical"])
        return {
            "response": (
                f"Disk: {data['percent_used']:.1f}% used "
                f"({data['used_gb']:.1f} GB / {data['total_gb']:.1f} GB) — {status}"
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
        mem_st = alert_status(mem["percent_used"], cfg["memory_warning"], cfg["memory_critical"])
        cpu_st = alert_status(cpu["percent_used"], cfg["cpu_warning"], cfg["cpu_critical"])
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
            "disk_status": disk_st,
            "memory_status": mem_st,
            "cpu_status": cpu_st,
            "uptime": uptime_str,
        }

    if intent == "alerts":
        from .db import get_alerts, unacked_count
        alerts = get_alerts(limit=5)
        count = unacked_count()
        if not alerts:
            return {"response": "No alerts recorded yet."}
        lines = [f"Recent alerts ({count} unacknowledged):"]
        for a in alerts:
            ack = "✓" if a["acked"] else "!"
            lines.append(f"  [{ack}] [{a['severity']}] {a['message']}  ({a['timestamp']})")
        return {"response": "\n".join(lines)}

    if intent == "runbooks":
        rbs = list_runbooks()
        lines = ["Available runbooks:"]
        for rb in rbs:
            lines.append(f"  run {rb['name']} — {rb['description']}")
        return {"response": "\n".join(lines)}

    if intent == "config":
        lines = ["Current thresholds:"]
        for k, v in cfg.items():
            lines.append(f"  {k}: {v}")
        return {"response": "\n".join(lines)}

    if intent == "logs":
        return {"response": "Usage: analyze logs: <paste log content here>"}

    if intent == "help":
        return {"response": help_text_action()}

    return {
        "response": (
            "I didn't understand that. Try: check disk, check memory, check cpu, "
            "top processes, system health, or type 'help' for all commands."
        )
    }
