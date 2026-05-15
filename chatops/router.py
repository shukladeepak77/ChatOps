import re
import os
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
    analyze_test_log,
    copy_ssh_key,
    get_prometheus_metrics,
    configure_prometheus_metrics,
    toggle_prometheus_metric,
    analyze_prometheus_metrics,
    PROMETHEUS_METRIC_KEYS,
)
from .config import load_config
from .runbooks import list_runbooks, request_runbook, confirm_runbook, cancel_runbook, dry_run_runbook

# Intent keyword map — order matters: more specific phrases listed first
_INTENTS: Dict[str, list] = {
    "logs":        ["analyze logs", "log analysis", "check logs", "analyze log", "parse logs"],
    "processes":   ["top processes", "running processes", "process list", "show processes", "ps aux", "top cpu processes", "high cpu process"],
    "ports":       ["open ports", "listening ports", "check ports", "network ports", "show ports"],
    "health":      ["system health", "system status", "system overview", "overall health", "how is system"],
    "runbooks":    ["list runbooks", "available runbooks", "show runbooks", "what runbooks"],
    "alerts":      ["show alerts", "recent alerts", "alert history", "view alerts", "list alerts"],
    "disk":        ["disk", "storage", "space", "filesystem", "drive", "how full", "disk usage"],
    "memory":      ["check memory", "memory usage", "ram usage", "mem usage", "check ram", "check mem", "check swap", "how much memory", "how much ram"],
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
    "users":       ["list users", "show users", "add user", "remove user", "user management"],
    "audit":       ["show audit", "audit log", "show audit log"],
}

_ALL_PHRASES = [
    (phrase, intent)
    for intent, phrases in _INTENTS.items()
    for phrase in phrases
]

_pending_restart: str | None = None
_pending_ssh_copy: str | None = None
_pending_kill: str | None = None


def _detect_intent(s: str) -> str:
    # Exact substring match first (faster and more reliable)
    for intent, keywords in _INTENTS.items():
        if any(kw in s for kw in keywords):
            return intent
    # Fuzzy fallback — only for short inputs (≤5 words) to avoid false positives on natural language
    if len(s.split()) <= 5:
        phrases = [p for p, _ in _ALL_PHRASES]
        result = rfuzz_process.extractOne(s, phrases, scorer=fuzz.WRatio, score_cutoff=88)
        if result:
            matched = result[0]
            for phrase, intent in _ALL_PHRASES:
                if phrase == matched:
                    return intent
    return "unknown"


def route_message(message: str, caller_role: str = "operator", _nlu_depth: int = 0) -> Dict[str, str]:
    global _pending_restart, _pending_ssh_copy, _pending_kill
    raw = (message or "").strip()
    raw_lower = raw.lower()
    # Allow - and . for node/service names
    s = re.sub(r"[^a-z0-9\s:_\-\.]", "", raw_lower).strip()

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

    if s in ("date", "show date", "current date", "what is the date", "what time is it"):
        from datetime import datetime
        now = datetime.now()
        return {"response": f"📅 {now.strftime('%A, %d %B %Y  %H:%M:%S')}"}

    # ── Command-help questions — answer from our own help system, not LLM ─────
    _CMD_HELP = {
        "list kb":              "Lists all Knowledge Base articles stored in ChatOps. Shows ID, title, tags, and creation date. Use 'show kb <id>' to read the full content of any article.",
        "add kb":               "Adds a new Knowledge Base article. Usage: add kb <Title>: <content>. Tags are optional but searchable. Only operators and above can add articles.",
        "show kb":              "Displays the full content of a Knowledge Base article by its ID. Usage: show kb <id>.",
        "search kb":            "Searches KB articles by keyword across title, content, and tags. Usage: search kb <keyword>.",
        "delete kb":            "Deletes a Knowledge Base article by ID. Admin role required. Usage: delete kb <id>.",
        "show analytics":       "Displays a 7-day summary with MTTR trend chart and team leaderboard. Append a period like '30d' for a different window.",
        "rca":                  "Generates an AI-drafted Root Cause Analysis for a specific alert. Usage: rca <alert_id>. Includes incident summary, root cause, timeline, impact, and action items.",
        "show tickets":         "Lists all open ITSM tickets with ID, priority, title, and created date.",
        "show all tickets":     "Lists all tickets (open and closed).",
        "show ticket":          "Shows full details of a specific ticket. Usage: show ticket <id>.",
        "create ticket":        "Creates a new ITSM ticket. Usage: create ticket <title> [priority high/medium/low].",
        "close ticket":         "Closes an open ticket by ID. Usage: close ticket <id>.",
        "link ticket":          "Links a ticket to an alert. Usage: link ticket <ticket_id> alert <alert_id>.",
        "show prometheus metrics": "Displays current Prometheus-format metrics inline. Includes alerts, MTTR, system usage, runbook count, KB size, and audit events (configurable).",
        "configure prometheus":    "Shows which Prometheus metrics are enabled or disabled. Toggle with 'enable metric <name>' or 'disable metric <name>'.",
        "enable metric":           "Enables a Prometheus metric by key name. Usage: enable metric <key>. See keys with 'configure prometheus'.",
        "disable metric":          "Disables a Prometheus metric by key name. Usage: disable metric <key>. See keys with 'configure prometheus'.",
        "analyze prometheus":      "Sends current Prometheus metrics to the AI for interpretation and action recommendations.",
        "show alerts":          "Lists the 20 most recent alerts with severity, message, and acknowledgement status.",
        "show predictive alerts": "Analyses recent metric trends and shows any metrics projected to breach a WARNING or CRITICAL threshold within the next 10 minutes.",
        "run test":             "Runs the full ChatOps pytest automation suite (266 tests). Requires developer or admin role. Results are saved as a timestamped log file.",
        "show test logs":       "Lists all past test-run log files with timestamp and size. Each entry has Open, Analyse with AI, and Delete buttons.",
        "dry run":              "Simulates a runbook without executing it. Safe preview of what would happen. Usage: dry run <runbook_name>.",
        "check disk":           "Shows current disk usage — total, used, free GB and percentage. Flags WARNING or CRITICAL based on configured thresholds.",
        "check memory":         "Shows RAM usage in MB with total, used, and percentage. Includes status badge.",
        "check cpu":            "Shows current CPU usage percentage and logical core count.",
        "check uptime":         "Shows how long the server has been running in days, hours, minutes.",
        "check ports":          "Lists all open/listening TCP and UDP ports on the server.",
        "system health":        "Full health summary — disk, memory, CPU, and uptime in one response with OK/WARNING/CRITICAL badges.",
        "top processes":        "Lists top 5 processes by CPU usage, showing PID, name, CPU%, and memory%.",
        "show services":        "Lists all active systemd services that have a running process ID. Supports optional keyword filter, e.g. 'show services nginx'.",
        "service status":       "Shows the current status of a specific systemd service. Usage: service status <name>.",
        "restart":              "Requests a restart of a named service with a confirmation step. Usage: restart <service>.",
        "check dns":            "Performs a DNS lookup for a domain — returns A, AAAA, MX, NS, TXT, and CNAME records. Usage: check dns <domain>.",
        "check ip":             "Shows all network interface IP addresses on the server.",
        "check routes":         "Displays the routing table.",
        "check connections":    "Lists active network connections.",
        "show report":          "Generates a system health report across all configured nodes.",
        "list runbooks":        "Shows all available runbooks with name and description.",
        "list nodes":           "Lists all configured nodes (servers) the platform monitors.",
        "add node":             "Registers a new remote node for monitoring. Usage: add node <name> <user@host>.",
        "list users":           "Lists all users with their roles and active status. Admin only.",
        "add user":             "Creates a new user account. Usage: add user <username> <password> <role>. Roles: viewer, operator, developer, admin.",
        "remove user":          "Deletes a user account. Admin only. Usage: remove user <username>.",
        "deactivate user":      "Disables a user's login without deleting them. Admin only.",
        "set role":             "Changes a user's role. Admin only. Usage: set role <username> <role>.",
        "show llm config":      "Shows the active LLM provider, model, and API key status. Admin only.",
        "explain alert":        "Uses AI to explain a specific alert and suggest remediation. Usage: explain alert <id>.",
        "analyze logs":         "Analyses pasted log content using AI — identifies severity, root cause, impact, and suggested actions.",
        "config":               "Shows current threshold configuration for disk, memory, and CPU warnings and critical levels.",
        "help":                 "Displays the full command reference grouped by category.",
        "date":                 "Shows the current server date and time.",
        "show system config":   "Shows enriched system info: hostname, IP, OS, live metrics, and ChatOps platform stats.",
        "kill process":         "Sends SIGTERM to a process by PID with a confirmation step. Usage: kill process <pid>.",
    }
    _cmd_q = re.match(
        r"^(?:what\s+is\s+(?:the\s+)?(?:purpose\s+of\s+)?|"
        r"what\s+does\s+|"
        r"explain\s+(?:the\s+)?(?:command\s+)?|"
        r"purpose\s+of\s+(?:the\s+)?(?:command\s+)?|"
        r"help\s+(?:with\s+|on\s+|for\s+)?(?:the\s+)?(?:command\s+)?|"
        r"how\s+(?:do\s+(?:i|we|you)\s+)?(?:to\s+)?(?:use\s+|run\s+|execute\s+)?(?:the\s+)?(?:command\s+)?)"
        r"['\"]?([\w\s]+?)['\"]?\s*(?:command|cmd)?\s*\??$",
        s,
    )
    if _cmd_q:
        query = _cmd_q.group(1).strip().lower()
        # exact match first, then prefix match
        desc = _CMD_HELP.get(query)
        if not desc:
            for key, val in _CMD_HELP.items():
                if query == key or query.startswith(key) or key.startswith(query):
                    desc = val
                    query = key
                    break
        if desc:
            return {"response": f"**{query}** — {desc}\n\nType `help` to see all commands."}

    if s in ("show test logs", "list test logs", "show test runs", "test logs"):
        if caller_role not in ("developer", "admin"):
            return {"response": "Access denied. Test logs are available to developer and admin roles only."}
        import glob
        log_dir = os.path.join(os.path.dirname(__file__), "..", "sample_logs")
        pattern = os.path.join(log_dir, "pytest_[0-9]*.log")
        files = sorted(glob.glob(pattern), reverse=True)
        if not files:
            return {"response": "No test run logs found."}
        entries = []
        for f in files:
            fname = os.path.basename(f)
            size_kb = os.path.getsize(f) // 1024
            # parse date from filename: pytest_YYYYMMDD_HHMMSS.log
            try:
                from datetime import datetime
                dt = datetime.strptime(fname, "pytest_%Y%m%d_%H%M%S.log")
                label = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                label = fname
            entries.append({"filename": fname, "label": label, "size_kb": size_kb})
        summary = f"Test Run Logs — {len(entries)} execution(s) found\n"
        summary += "\n".join(f"  {e['label']}  ({e['size_kb']} KB)  {e['filename']}" for e in entries)
        return {"response": summary, "test_logs": entries}

    if re.match(r"^run\s+tests?(\s+suite)?$", s) or s in ("pytest", "test suite", "run test cases", "run chatops tests", "run test suite"):
        if caller_role not in ("developer", "admin"):
            return {"response": "Access denied. 'run test' is available to developer and admin roles only."}
        return run_tests()

    test_log_m = re.match(r"^analyze\s+test\s+log\s+(pytest_\S+\.log)$", s)
    if test_log_m:
        if caller_role not in ("developer", "admin"):
            return {"response": "Access denied. Test log analysis is available to developer and admin roles only."}
        return analyze_test_log(test_log_m.group(1))

    # Inline log analysis
    log_match = re.match(r"^(?:analyze\s+logs?|check\s+logs?)\s*:?\s+(.+)$", s, re.DOTALL)
    if log_match:
        logs = log_match.group(1).strip()
        placeholder = re.sub(r'\s+', ' ', logs).lower()
        if placeholder in ("<paste log content here>", "paste log content here", "<content>", "content"):
            return {"response": "Usage: analyze logs: <paste log content here>\nYou can also upload a log file using the Upload Log button."}
        from .llm import ask as _llm_ask, is_configured as _llm_ok
        if _llm_ok():
            llm_prompt = (
                "Analyze the following log content. Identify:\n"
                "1. Severity (HIGH / MEDIUM / LOW)\n"
                "2. Root cause\n"
                "3. Impact\n"
                "4. Suggested actions\n\n"
                f"Log content:\n{logs[:3000]}"
            )
            answer = _llm_ask(
                llm_prompt,
                system="You are a DevOps engineer expert in log analysis. Be concise and technical. Keep response under 200 words.",
            )
            return {"response": f"Log Analysis (AI):\n{answer}"}
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
    svc_status_m = re.match(r'^service\s+status\s+([\w\-\.]+)$', s)
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

    restart_m = re.match(r'^restart\s+([\w\-\.]+)$', s)
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

    confirm_restart_m = re.match(r'^confirm\s+restart\s+([\w\-\.]+)$', s)
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

    # Runbook: dry run <name>
    dry_run_match = re.match(r"^(?:dry[\s\-]run|run\s+[\w\-]+\s+--dry[\-\s]?run)\s*([\w\-]*)", s)
    if not dry_run_match:
        dry_run_match = re.match(r"^dry[\s\-]?run\s+([\w\-]+)", s)
    if dry_run_match:
        name = dry_run_match.group(1).strip()
        if name:
            result = dry_run_runbook(name)
            if result["status"] == "ok":
                return {"response": result["output"]}
            return {"response": result["message"]}

    # Runbook: run <name> — only match known runbook names to avoid swallowing NL sentences
    _KNOWN_RUNBOOKS = {"clear_tmp", "disk_breakdown", "large_logs", "listening_services",
                       "flush_cache", "rotate_logs", "rotate_secret"}
    run_match = re.match(r"^run\s+([\w\-]+)", s)
    if run_match and run_match.group(1) in _KNOWN_RUNBOOKS:
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
        _pending_kill = None
        result = cancel_runbook()
        return {"response": result["message"]}

    # ── User management commands (admin only) ──────────────────────────────────
    _USER_MGMT_PATTERNS = (
        r'^add\s+user\b', r'^deactivate\s+user\b', r'^remove\s+user\b',
        r'^set\s+role\b',
    )
    _is_user_cmd = any(re.match(p, s) for p in _USER_MGMT_PATTERNS) or s in ("list users", "show users")
    if _is_user_cmd and caller_role != "admin":
        return {"response": "Access denied. User management commands are available to admin users only."}

    if re.match(r'^add\s+user\b', s) and not re.match(r'^add\s+user\s+(\S+)\s+(\S+)\s+(viewer|operator|developer|admin)$', s):
        return {"response": (
            "Invalid syntax. Usage:\n"
            "  add user &lt;username&gt; &lt;password&gt; &lt;viewer|operator|developer|admin&gt;\n\n"
            "Example:\n"
            "  add user john secret123 operator"
        )}

    add_user_m = re.match(r'^add\s+user\s+(\S+)\s+(\S+)\s+(viewer|operator|developer|admin)$', s)
    if add_user_m:
        from .db import create_user as _db_create_user
        from chatops.auth import hash_password as _hp
        uname, pwd, role = add_user_m.group(1), add_user_m.group(2), add_user_m.group(3)
        ok = _db_create_user(uname, _hp(pwd), role)
        if ok:
            return {"response": f"User '{uname}' created with role '{role}'."}
        return {"response": f"User '{uname}' already exists."}

    deactivate_user_m = re.match(r'^deactivate\s+user\s+(\S+)$', s)
    if deactivate_user_m:
        from .db import set_user_active as _set_active
        uname = deactivate_user_m.group(1)
        if uname == "admin":
            return {"response": "Cannot deactivate the admin user."}
        ok = _set_active(uname, False)
        if ok:
            return {"response": f"User '{uname}' deactivated."}
        return {"response": f"User '{uname}' not found."}

    remove_user_m = re.match(r'^remove\s+user\s+(\S+)$', s)
    if remove_user_m:
        from .db import delete_user as _delete_user
        uname = remove_user_m.group(1)
        if uname == "admin":
            return {"response": "Cannot remove the admin user."}
        ok = _delete_user(uname)
        if ok:
            return {"response": f"User '{uname}' deleted."}
        return {"response": f"User '{uname}' not found."}

    if re.match(r'^set\s+role\b', s) and not re.match(r'^set\s+role\s+(\S+)\s+(viewer|operator|developer|admin)$', s):
        return {"response": (
            "Invalid syntax. Usage:\n"
            "  set role &lt;username&gt; &lt;viewer|operator|developer|admin&gt;\n\n"
            "Example:\n"
            "  set role john operator"
        )}

    set_role_m = re.match(r'^set\s+role\s+(\S+)\s+(viewer|operator|developer|admin)$', s)
    if set_role_m:
        from .db import update_user_role as _update_role
        uname, role = set_role_m.group(1), set_role_m.group(2)
        ok = _update_role(uname, role)
        if ok:
            return {"response": f"User '{uname}' role updated to '{role}'."}
        return {"response": f"User '{uname}' not found."}

    if s in ("list users", "show users"):
        from .db import list_users as _list_users
        users = _list_users()
        if not users:
            return {"response": "No users found."}
        lines = ["Users:"]
        for u in users:
            status = "active" if u["active"] else "inactive"
            lines.append(f"  {u['username']} — {u['role']} ({status})")
        return {"response": "\n".join(lines)}

    if s in ("show audit log", "audit log", "show audit"):
        from .db import get_audit_log as _get_audit
        logs = _get_audit(limit=10)
        if not logs:
            return {"response": "No audit log entries yet."}
        lines = ["Recent audit log (last 10):"]
        for entry in logs:
            ts = (entry.get("timestamp") or "")[:16]
            lines.append(f"  [{ts}] {entry['username']}: {entry['command']}")
        return {"response": "\n".join(lines)}

    # ── LLM config commands ────────────────────────────────────────────────────
    llm_provider_m = re.match(r'^config\s+set\s+llm\s+provider\s+(\S+)$', s)
    if llm_provider_m:
        from .config import save_config as _sc
        from .llm import _VALID_PROVIDERS
        provider = llm_provider_m.group(1).lower()
        if provider not in _VALID_PROVIDERS:
            return {"response": f"Unknown provider '{provider}'. Choose: {', '.join(_VALID_PROVIDERS)}"}
        _sc({"llm_provider": provider})
        return {"response": f"LLM provider set to '{provider}'."}

    # config set llm api key <key>  — preserve case
    llm_key_m = re.match(r'^config\s+set\s+llm\s+api[\s_-]?key\s+(\S+)$', raw, re.IGNORECASE)
    if llm_key_m:
        from .config import save_config as _sc
        _sc({"llm_api_key": llm_key_m.group(1)})
        return {"response": "LLM API key saved."}

    llm_model_m = re.match(r'^config\s+set\s+llm\s+model\s+(\S+)$', raw, re.IGNORECASE)
    if llm_model_m:
        from .config import save_config as _sc
        _sc({"llm_model": llm_model_m.group(1)})
        return {"response": f"LLM model set to '{llm_model_m.group(1)}'."}

    llm_url_m = re.match(r'^config\s+set\s+ollama[\s_-]?url\s+(\S+)$', raw, re.IGNORECASE)
    if llm_url_m:
        from .config import save_config as _sc
        _sc({"ollama_url": llm_url_m.group(1)})
        return {"response": f"Ollama URL set to '{llm_url_m.group(1)}'."}

    # test llm
    if s == "test llm":
        from .llm import ask as _llm_ask, is_configured as _llm_ok
        if not _llm_ok():
            return {"response": "LLM not configured. Use:\n  config set llm provider <ollama|groq|claude>\n  config set llm api key <key>  (groq/claude only)"}
        result = _llm_ask("Reply with exactly: LLM OK", system="You are a test responder.")
        return {"response": f"LLM test: {result}"}

    # explain alert <id>
    explain_m = re.match(r'^explain\s+alert\s+(\d+)$', s)
    if explain_m:
        from .db import get_alerts as _get_alerts
        from .llm import ask as _llm_ask, is_configured as _llm_ok
        if not _llm_ok():
            return {"response": "LLM not configured. Use: config set llm provider <ollama|groq|claude>"}
        alert_id = int(explain_m.group(1))
        alerts = _get_alerts(limit=500)
        alert = next((a for a in alerts if a["id"] == alert_id), None)
        if not alert:
            return {"response": f"Alert #{alert_id} not found."}
        prompt = (
            f"Alert: {alert['message']}\n"
            f"Severity: {alert['severity']}\n"
            f"Node: {alert['node']}\n"
            f"Time: {alert['timestamp']}\n\n"
            f"In 2-3 sentences: what is the likely root cause, and what is the single most important action to take?"
        )
        rca = _llm_ask(prompt)
        return {
            "response": (
                f"Alert #{alert_id} — {alert['severity']}\n"
                f"{alert['message']}\n\n"
                f"RCA:\n{rca}"
            )
        }

    # config set slack_webhook <url>  — match case-insensitively but preserve original URL case
    slack_cfg_m = re.match(r'^config\s+set\s+slack[-_]?webhook\s+(\S+)$', raw, re.IGNORECASE)
    if slack_cfg_m:
        from .config import save_config as _save_config
        url = slack_cfg_m.group(1)
        _save_config({"slack_webhook": url})
        return {"response": "Slack webhook configured. CRITICAL alerts will be sent to Slack."}

    slack_token_m = re.match(r'^config\s+set\s+slack\s+bot\s+token\s+(\S+)$', raw, re.IGNORECASE)
    if slack_token_m:
        from .config import save_config as _save_config
        _save_config({"slack_bot_token": slack_token_m.group(1)})
        return {"response": "Slack bot token saved. Inbound Slack commands are now enabled."}

    slack_secret_m = re.match(r'^config\s+set\s+slack\s+signing\s+secret\s+(\S+)$', raw, re.IGNORECASE)
    if slack_secret_m:
        from .config import save_config as _save_config
        _save_config({"slack_signing_secret": slack_secret_m.group(1)})
        return {"response": "Slack signing secret saved."}

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

    # ── Analytics ──────────────────────────────────────────────────────────────
    analytics_m = re.match(r'^show\s+analytics(?:\s+(\d+)d?)?$', s)
    if analytics_m or s in ("analytics", "show analytics"):
        days = int(analytics_m.group(1)) if analytics_m and analytics_m.group(1) else 7
        from .analytics import get_alert_stats, get_mttr_stats, get_command_stats, get_mttr_trend, get_user_leaderboard
        a = get_alert_stats(days)
        m = get_mttr_stats(days)
        cmds = get_command_stats(days)
        mttr_trend = get_mttr_trend(days)
        leaderboard = get_user_leaderboard(days)
        sev_line = "  ".join(f"{k}: {v}" for k, v in sorted(a["by_severity"].items())) or "none"
        mttr_line = (f"{m['avg_minutes']} min avg  (min {m['min_minutes']}  max {m['max_minutes']}  n={m['sample_size']})"
                     if m.get("avg_minutes") else "no resolved alerts")
        lines = [
            f"Analytics — last {days} days",
            "",
            "Alerts:",
            f"  Total:       {a['total']}  (acked: {a['acked']}  unacked: {a['unacked']})",
            f"  By severity: {sev_line}",
            "",
            "MTTR:",
            f"  {mttr_line}",
            "",
            "Top commands:",
        ]
        for c in cmds[:5]:
            lines.append(f"  {c['command'][:50]:<50}  {c['count']}x")
        return {
            "response": "\n".join(lines),
            "pdf_report": True,
            "pdf_days": days,
            "mttr_trend": mttr_trend,
            "leaderboard": leaderboard,
        }

    # ── Prometheus metrics ─────────────────────────────────────────────────────
    if s in ("prometheus", "show prometheus", "prometheus metrics", "show prometheus metrics", "metrics"):
        return get_prometheus_metrics()

    if s in ("configure prometheus", "prometheus config", "prometheus settings", "show prometheus config"):
        return configure_prometheus_metrics()

    _enable_m = re.match(r'^(enable|disable)\s+(?:metric\s+)?(\S[\w\s]*)$', s)
    if _enable_m and _enable_m.group(2).strip() in PROMETHEUS_METRIC_KEYS:
        return toggle_prometheus_metric(_enable_m.group(2).strip(), _enable_m.group(1) == "enable")

    if s in ("analyze prometheus", "analyse prometheus", "analyze prometheus metrics",
             "analyse prometheus metrics", "ai prometheus", "prometheus ai"):
        # Use last known metrics text — re-fetch inline
        result = get_prometheus_metrics()
        raw = result.get("prometheus_output", result.get("response", ""))
        raw_clean = raw.replace("```", "").strip()
        return analyze_prometheus_metrics(raw_clean)

    # ── Knowledge Base ─────────────────────────────────────────────────────────
    if s in ("list kb", "show kb", "kb list"):
        from .db import kb_list as _kb_list
        articles = _kb_list()
        if not articles:
            return {"response": "Knowledge base is empty.\nUse: add kb <title>: <content>"}
        lines = [f"Knowledge Base ({len(articles)} articles):"]
        for a in articles:
            tags = f"  [{a['tags']}]" if a['tags'] else ""
            lines.append(f"  #{a['id']}  {a['title']}{tags}  — by {a['created_by']} on {a['created_at'][:10]}")
        lines.append("\nUse  show kb <id>  to read an article.")
        return {"response": "\n".join(lines)}

    show_kb_m = re.match(r'^show\s+kb\s+(\d+)$', s)
    if show_kb_m:
        from .db import kb_get as _kb_get
        article = _kb_get(int(show_kb_m.group(1)))
        if not article:
            return {"response": f"No KB article with ID {show_kb_m.group(1)}."}
        tags = f"\nTags: {article['tags']}" if article['tags'] else ""
        return {"response": f"KB #{article['id']}: {article['title']}{tags}\nBy: {article['created_by']}  on  {article['created_at'][:10]}\n\n{article['content']}"}

    search_kb_m = re.match(r'^(?:search\s+kb|kb\s+search)\s+(.+)$', s)
    if search_kb_m:
        from .db import kb_search as _kb_search
        query = search_kb_m.group(1).strip()
        results = _kb_search(query)
        if not results:
            return {"response": f"No KB articles found matching '{query}'."}
        lines = [f"KB results for '{query}' ({len(results)} found):"]
        for a in results:
            tags = f"  [{a['tags']}]" if a['tags'] else ""
            lines.append(f"  #{a['id']}  {a['title']}{tags}")
        lines.append("\nUse  show kb <id>  to read an article.")
        return {"response": "\n".join(lines)}

    add_kb_m = re.match(r'^add\s+kb\s+(.+?)\s*:\s*(.+)$', raw, re.DOTALL)
    if add_kb_m:
        from .db import kb_add as _kb_add
        title, content = add_kb_m.group(1).strip(), add_kb_m.group(2).strip()
        aid = _kb_add(title, content, created_by=caller_role)
        return {"response": f"KB article #{aid} added: '{title}'"}

    delete_kb_m = re.match(r'^delete\s+kb\s+(\d+)$', s)
    if delete_kb_m:
        if caller_role != "admin":
            return {"response": "Access denied. Only admins can delete KB articles."}
        from .db import kb_delete as _kb_delete
        ok = _kb_delete(int(delete_kb_m.group(1)))
        if ok:
            return {"response": f"KB article #{delete_kb_m.group(1)} deleted."}
        return {"response": f"No KB article with ID {delete_kb_m.group(1)}."}

    # ── RCA Draft ──────────────────────────────────────────────────────────────
    rca_m = re.match(r'^rca\s+(\d+)$', s)
    if rca_m or s == "rca":
        if not rca_m:
            return {"response": "Usage: `rca <alert_id>` — e.g. `rca 42`"}
        from .actions import generate_rca
        return generate_rca(int(rca_m.group(1)))

    # ── ITSM Tickets ───────────────────────────────────────────────────────────
    if s in ("show tickets", "list tickets", "tickets"):
        from .db import ticket_list
        tickets = ticket_list(status="open")
        if not tickets:
            return {"response": "No open tickets.\nUse `create ticket <title>` to create one."}
        lines = [f"Open Tickets ({len(tickets)}):"]
        for t in tickets:
            pri_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "⚪")
            lines.append(f"  #{t['id']}  {pri_icon} [{t['priority'].upper()}]  {t['title'][:60]}  ({t['created_at'][:10]})")
        return {"response": "\n".join(lines), "tickets": tickets}

    if s in ("show all tickets", "list all tickets", "all tickets"):
        from .db import ticket_list
        tickets = ticket_list(status="all")
        if not tickets:
            return {"response": "No tickets found."}
        lines = [f"All Tickets ({len(tickets)}):"]
        for t in tickets:
            pri_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "⚪")
            status_icon = "✅" if t["status"] == "closed" else "🔓"
            lines.append(f"  #{t['id']}  {status_icon} {pri_icon} [{t['priority'].upper()}]  {t['title'][:55]}  ({t['created_at'][:10]})")
        return {"response": "\n".join(lines), "tickets": tickets}

    show_ticket_m = re.match(r'^show\s+ticket\s+(\d+)$', s)
    if show_ticket_m:
        from .db import ticket_get
        t = ticket_get(int(show_ticket_m.group(1)))
        if not t:
            return {"response": f"Ticket #{show_ticket_m.group(1)} not found."}
        pri_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "⚪")
        lines = [
            f"Ticket #{t['id']} — {t['title']}",
            f"  Status:      {t['status'].upper()}",
            f"  Priority:    {pri_icon} {t['priority'].upper()}",
            f"  Created by:  {t['created_by']}",
            f"  Created at:  {t['created_at'][:16]}",
        ]
        if t.get("alert_id"):
            lines.append(f"  Linked alert: #{t['alert_id']}")
        if t.get("closed_at"):
            lines.append(f"  Closed at:   {t['closed_at'][:16]}")
        if t.get("description"):
            lines += ["", "Description:", f"  {t['description']}"]
        return {"response": "\n".join(lines)}

    create_ticket_m = re.match(r'^create\s+ticket\s+(.+)$', s)
    if create_ticket_m:
        title = create_ticket_m.group(1).strip()
        # Check for priority hint: "create ticket <title> priority high/medium/low"
        pri_m = re.search(r'\bpriority\s+(high|medium|low)\b', title, re.IGNORECASE)
        priority = pri_m.group(1).lower() if pri_m else "medium"
        if pri_m:
            title = title[:pri_m.start()].strip()
        from .db import ticket_create
        tid = ticket_create(title=title, priority=priority, created_by=caller_role)
        return {"response": f"Ticket #{tid} created: **{title}** [{priority.upper()}]\nUse `show ticket {tid}` to view details."}

    close_ticket_m = re.match(r'^close\s+ticket\s+(\d+)$', s)
    if close_ticket_m:
        from .db import ticket_close
        ok = ticket_close(int(close_ticket_m.group(1)))
        if ok:
            return {"response": f"Ticket #{close_ticket_m.group(1)} closed."}
        return {"response": f"Ticket #{close_ticket_m.group(1)} not found or already closed."}

    link_ticket_m = re.match(r'^link\s+ticket\s+(\d+)\s+alert\s+(\d+)$', s)
    if link_ticket_m:
        from .db import ticket_update
        ok = ticket_update(int(link_ticket_m.group(1)), status="open")
        if ok:
            # Update alert_id directly
            from .db import _conn as _dbconn
            with _dbconn() as conn:
                conn.execute("UPDATE tickets SET alert_id=?, updated_at=datetime('now') WHERE id=?",
                             (int(link_ticket_m.group(2)), int(link_ticket_m.group(1))))
            return {"response": f"Ticket #{link_ticket_m.group(1)} linked to alert #{link_ticket_m.group(2)}."}
        return {"response": f"Ticket #{link_ticket_m.group(1)} not found."}

    # ── Kill process ───────────────────────────────────────────────────────────
    kill_m = re.match(r'^kill\s+process\s+(\d+)$', s)
    if kill_m:
        pid = kill_m.group(1)
        import subprocess
        try:
            out = subprocess.check_output(["ps", "-p", pid, "-o", "pid=,comm=,args="], text=True).strip()
            if not out:
                return {"response": f"No process found with PID {pid}."}
            _pending_kill = pid
            return {"response": (
                f"Process {pid}: {out}\n\n"
                f"Type  confirm kill {pid}  to terminate it, or  cancel  to abort."
            )}
        except subprocess.CalledProcessError:
            return {"response": f"No process found with PID {pid}."}

    confirm_kill_m = re.match(r'^confirm\s+kill\s+(\d+)$', s)
    if confirm_kill_m:
        pid = confirm_kill_m.group(1)
        if _pending_kill != pid:
            return {"response": f"No pending kill for PID {pid}. Run  kill process {pid}  first."}
        _pending_kill = None
        import subprocess, signal
        try:
            subprocess.run(["kill", "-TERM", pid], check=True)
            return {"response": f"SIGTERM sent to process {pid}."}
        except subprocess.CalledProcessError:
            return {"response": f"Failed to kill PID {pid}. Process may have already exited or requires elevated privileges."}


    _svc_m = re.match(r'^(?:show|list|search)\s+services?\s+(.+)$', s)
    _svc_filter = _svc_m.group(1).strip() if _svc_m else None
    if s in ("show services", "list services") or _svc_m:
        import subprocess
        try:
            names_out = subprocess.check_output(
                ["systemctl", "list-units", "--type=service", "--all",
                 "--no-pager", "--plain", "--no-legend"],
                text=True, timeout=10
            )
            names = [l.split()[0] for l in names_out.strip().splitlines() if l.strip()]
            if not names:
                return {"response": "No services found."}

            props_out = subprocess.check_output(
                ["systemctl", "show", "--property=Id,ActiveState,SubState,MainPID"] + names,
                text=True, timeout=15
            )
            pid_map = {}
            current = {}
            for line in props_out.splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    current[k] = v
                elif not line.strip() and current.get("Id"):
                    pid_map[current["Id"]] = current
                    current = {}
            if current.get("Id"):
                pid_map[current["Id"]] = current

            lines = []
            for line in names_out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    name, active, sub = parts[0], parts[2], parts[3]
                    props = pid_map.get(name, {})
                    pid = props.get("MainPID", "0")
                    if pid == "0":
                        continue
                    if _svc_filter and _svc_filter not in name:
                        continue
                    lines.append(f"  {name:<45} {active}/{sub:<10}  PID: {pid}")
            if not lines:
                label = f"No services matching '{_svc_filter}'." if _svc_filter else "No services found."
                return {"response": label}
            if _svc_filter:
                return {"response": f"Services matching '{_svc_filter}' ({len(lines)} found):\n" + "\n".join(lines)}
            return {"response": f"Services ({len(lines)} total):\n" + "\n".join(lines) + "\n\nTip: type  show services <keyword>  to filter  e.g. show services ssh"}
        except Exception as e:
            return {"response": f"Could not list services: {e}"}

    # ── Intent detection ───────────────────────────────────────────────────────
    intent = _detect_intent(s)

    if s in ("show predictive alerts", "predictive alerts", "check predictive"):
        from .predictive import check_predictive_alerts
        alerts = check_predictive_alerts()
        if not alerts:
            return {"response": "No metrics currently trending toward a threshold breach."}
        lines = ["Predictive Alerts — metrics trending toward threshold:"]
        for a in alerts:
            lines.append(
                f"  ⚠ {a['metric'].capitalize()}: {a['current']}% now → "
                f"~{a['projected']}% in {a['eta_minutes']} min "
                f"(threshold: {a['threshold_value']}% {a['threshold_type']})"
            )
        return {"response": "\n".join(lines)}

    # ── Explicit alert filter commands ─────────────────────────────────────────
    _alerts_n_m = re.match(r'^show\s+alerts?\s+(\d+)$', s)
    if s in ("show unacked alerts", "unacked alerts", "show unacknowledged alerts", "unacknowledged alerts"):
        from .db import get_alerts
        alerts = [a for a in get_alerts(limit=100) if not a["acked"]]
        if not alerts:
            return {"response": "No unacknowledged alerts."}
        lines = [f"Unacknowledged alerts ({len(alerts)}):"]
        for a in alerts:
            lines.append(f"  #{a['id']} [{a['severity']}] {a['message']}  ({a['timestamp'][:16]})")
        return {"response": "\n".join(lines)}

    if s in ("show critical alerts", "critical alerts"):
        from .db import get_alerts
        alerts = [a for a in get_alerts(limit=100) if a["severity"] == "CRITICAL"]
        if not alerts:
            return {"response": "No CRITICAL alerts."}
        lines = [f"Critical alerts ({len(alerts)}):"]
        for a in alerts:
            ack = "✓" if a["acked"] else "!"
            lines.append(f"  #{a['id']} [{ack}] {a['message']}  ({a['timestamp'][:16]})")
        return {"response": "\n".join(lines)}

    if _alerts_n_m:
        from .db import get_alerts, unacked_count
        n = int(_alerts_n_m.group(1))
        alerts = get_alerts(limit=n)
        count = unacked_count()
        if not alerts:
            return {"response": "No alerts recorded yet."}
        lines = [f"Last {n} alerts ({count} unacknowledged):"]
        for a in alerts:
            ack = "✓" if a["acked"] else "!"
            lines.append(f"  #{a['id']} [{ack}] [{a['severity']}] {a['message']}  ({a['timestamp'][:16]})")
        return {"response": "\n".join(lines)}

    # ── Intents handled locally even when a node is specified ─────────────────
    if intent == "alerts":
        from .db import get_alerts, unacked_count
        node_filter = target_node if target_node and target_node != "all" else None
        alerts = get_alerts(limit=20, node=node_filter)
        count = unacked_count(node=node_filter)
        scope = f" for [{node_filter}]" if node_filter else ""
        if not alerts:
            return {"response": f"No alerts recorded{scope} yet."}
        lines = [f"Recent alerts{scope} ({count} unacknowledged):"]
        for a in alerts:
            ack = "✓" if a["acked"] else "!"
            lines.append(f"  #{a['id']} [{ack}] [{a['severity']}] {a['message']}  ({a['timestamp']})")
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

    if s in ("show llm config", "llm config", "llm status"):
        if caller_role != "admin":
            return {"response": "Access denied. This command is available to admin users only."}
        llm_provider = cfg.get("llm_provider", "none")
        llm_model_cfg = cfg.get("llm_model", "")
        from .llm import _DEFAULT_MODELS, is_configured as _llm_ok
        llm_model_display = llm_model_cfg or _DEFAULT_MODELS.get(llm_provider, "-")
        llm_key = cfg.get("llm_api_key", "")
        llm_key_display = ("*" * 6 + llm_key[-4:]) if len(llm_key) > 4 else ("(not set)" if not llm_key else llm_key)
        status = "Active" if _llm_ok() else "Not configured"
        lines = [
            "LLM Configuration (admin only)",
            "",
            f"  Status:    {status}",
            f"  Provider:  {llm_provider}",
            f"  Model:     {llm_model_display}",
            f"  API Key:   {llm_key_display}",
            f"  Ollama URL:{cfg.get('ollama_url', 'http://localhost:11434')}",
        ]
        return {"response": "\n".join(lines)}

    if intent == "config":
        import socket as _sock, platform, subprocess as _sp
        webhook = cfg.get("slack_webhook", "")
        webhook_display = webhook if webhook else "(not configured)"
        report_status = "Enabled" if cfg.get("report_enabled") else "Disabled"
        llm_provider = cfg.get("llm_provider", "none")
        llm_model_cfg = cfg.get("llm_model", "")
        from .llm import _DEFAULT_MODELS, is_configured as _llm_ok
        llm_model_display = llm_model_cfg or _DEFAULT_MODELS.get(llm_provider, "-")
        llm_key = cfg.get("llm_api_key", "")
        llm_key_display = ("*" * 6 + llm_key[-4:]) if len(llm_key) > 4 else ("(not set)" if not llm_key else llm_key)
        llm_status = "Active" if _llm_ok() else "Not configured"

        disk = check_disk()
        mem  = check_memory()
        cpu  = check_cpu()
        up   = check_uptime()
        uptime_str = f"{up['uptime_days']}d {up['uptime_hours']}h {up['uptime_minutes']}m"

        try:
            hostname = _sock.gethostname()
            local_ip = _sock.gethostbyname(hostname)
        except Exception:
            hostname, local_ip = "-", "-"

        try:
            os_info = platform.freedesktop_os_release().get("PRETTY_NAME", platform.system())
        except Exception:
            os_info = platform.system()

        try:
            kernel = _sp.check_output(["uname", "-r"], text=True).strip()
        except Exception:
            kernel = "-"

        from .nodes import list_nodes as _list_nodes
        node_count = len(_list_nodes())

        from .db import list_users as _list_users, get_alerts
        user_count = len(_list_users())
        alert_count = get_alerts(limit=1000)
        unacked = sum(1 for a in alert_count if not a.get("acked"))

        lines = [
            "System Configuration",
            "",
            "Server:",
            f"  Hostname:  {hostname}",
            f"  IP:        {local_ip}",
            f"  OS:        {os_info}",
            f"  Kernel:    {kernel}",
            f"  Uptime:    {uptime_str}",
            "",
            "Live Metrics:",
            f"  Disk:      {disk['percent_used']:.1f}% used  ({disk['used_gb']}GB / {disk['total_gb']}GB)",
            f"  Memory:    {mem['percent_used']:.1f}% used  ({mem['used_mb']}MB / {mem['total_mb']}MB)",
            f"  CPU:       {cpu['percent_used']:.1f}%  ({cpu['cpu_count']} cores)",
            "",
            "ChatOps:",
            f"  Nodes:     {node_count} registered",
            f"  Users:     {user_count}",
            f"  Alerts:    {unacked} unacknowledged",
            "",
            "Alert Thresholds:",
            f"  Disk:      warn {cfg.get('disk_warning')}%  critical {cfg.get('disk_critical')}%",
            f"  Memory:    warn {cfg.get('memory_warning')}%  critical {cfg.get('memory_critical')}%",
            f"  CPU:       warn {cfg.get('cpu_warning')}%  critical {cfg.get('cpu_critical')}%",
            f"  Interval:  {cfg.get('health_check_interval')}s",
            f"  Suppress:  {cfg.get('alert_suppress_minutes')} minutes",
            "",
            "Slack:",
            f"  Webhook:   {webhook_display}",
            "",
            "Daily Report:",
            f"  Status:    {report_status}",
            f"  Hour:      {cfg.get('report_hour', 8):02d}:00",
            "",
            "LLM / AI:",
            f"  Status:    {llm_status}",
            f"  Provider:  {llm_provider}",
            f"  Model:     {llm_model_display}",
            f"  API Key:   {llm_key_display}",
            f"  Ollama URL:{cfg.get('ollama_url', 'http://localhost:11434')}",
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
        dns_m = re.match(r'^check\s+dns\s+([\w\.\-]+)$', s)
        if dns_m:
            domain = dns_m.group(1)
            import socket, time
            try:
                import dns.resolver
            except ImportError:
                return {"response": "dnspython not installed. Run: pip install dnspython"}
            lines = [f"DNS details for {domain}:"]
            record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]
            for rtype in record_types:
                try:
                    answers = dns.resolver.resolve(domain, rtype, lifetime=6)
                    lines.append(f"\n  {rtype} records:")
                    for r in answers:
                        lines.append(f"    {r.to_text()}  (TTL: {answers.rrset.ttl}s)")
                except dns.resolver.NoAnswer:
                    pass
                except dns.resolver.NXDOMAIN:
                    return {"response": f"Domain not found: {domain}"}
                except Exception:
                    pass
            try:
                start = time.time()
                ip = socket.gethostbyname(domain)
                latency = round((time.time() - start) * 1000, 2)
                lines.append(f"\n  Resolved IP: {ip}  (latency: {latency}ms)")
            except Exception as e:
                lines.append(f"\n  Resolution failed: {e}")
            if len(lines) == 1:
                return {"response": f"No DNS records found for {domain}."}
            return {"response": "\n".join(lines)}

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

    # ── NLU fallback: map natural language to a command or answer directly ───────
    from .llm import ask as _llm_ask, is_configured as _llm_ok
    if _llm_ok() and raw and _nlu_depth == 0:
        _NLU_COMMANDS = (
            "check disk | check memory | check cpu | check uptime | check ports | "
            "top processes | system health | show predictive alerts | "
            "show alerts | show alerts <N> | show critical alerts | show unacked alerts | "
            "show services | show services <keyword> | service status <name> | "
            "restart <name> | check failed services | kill process <pid> | "
            "list runbooks | run <runbook> | dry run <runbook> | "
            "show tickets | show all tickets | show ticket <id> | "
            "create ticket <title> [priority high|medium|low] | close ticket <id> | "
            "link ticket <id> alert <id> | "
            "list kb | search kb <keyword> | show kb <id> | "
            "add kb <title>: <content> | delete kb <id> | "
            "check ip | check routes | check network | check connections | "
            "check dns | check dns <domain> | "
            "show analytics | show analytics <N>d | show prometheus metrics | "
            "configure prometheus | enable metric <name> | disable metric <name> | "
            "analyze prometheus | rca <alert_id> | explain alert <id> | "
            "analyze logs: <content> | analyze test log <filename> | "
            "show audit log | show report | show system config | "
            "add node <name> <user>@<host> | list nodes | remove node <name> | "
            "list users | add user <username> <password> <role> | "
            "set role <username> <role> | deactivate user <username> | "
            "run tests | show test logs | test llm | date | help"
        )
        _nlu_system = (
            "You are a command router for a ChatOps platform. "
            "The user has typed a natural language message that did not match any known command. "
            "Your job is to either:\n"
            "1. Map it to an exact command from the list below and reply ONLY with: EXECUTE: <command>\n"
            "2. If it is a general DevOps/Linux/ops question with no direct command match, answer it in under 150 words.\n"
            "3. If it is completely unrelated to operations (weather, sports, cooking, etc.), reply: UNKNOWN\n\n"
            "Rules:\n"
            "- Only use EXECUTE: if you are confident the user wants that specific action.\n"
            "- Fill in parameters exactly as shown in the command syntax. Examples:\n"
            "    'check if nginx is running' → EXECUTE: service status nginx\n"
            "    'run rca on alert 1' → EXECUTE: rca 1\n"
            "    'generate rca for alert 5' → EXECUTE: rca 5\n"
            "    'show me open tickets' → EXECUTE: show tickets\n"
            "    'how full is the disk' → EXECUTE: check disk\n"
            "- Parameters are positional numbers or names — never use key=value format.\n"
            "- Never guess a parameter that is not explicitly in the user's message.\n\n"
            f"Available commands:\n{_NLU_COMMANDS}"
        )
        nlu_result = _llm_ask(raw, system=_nlu_system)
        nlu_clean = nlu_result.strip()

        if nlu_clean.upper().startswith("EXECUTE:"):
            cmd = nlu_clean[len("EXECUTE:"):].strip()
            routed = route_message(cmd, caller_role=caller_role, _nlu_depth=1)
            # Prepend a subtle note showing what command was inferred
            routed["response"] = f"_(mapped: `{cmd}`)_\n\n{routed['response']}"
            return routed

        if nlu_clean.upper() == "UNKNOWN":
            return {
                "response": (
                    "I didn't understand that. Type `help` to see all available commands."
                )
            }

        return {"response": nlu_result}

    return {
        "response": (
            "I didn't understand that. Type `help` to see all available commands."
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
