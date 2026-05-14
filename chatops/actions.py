import shutil
import os
import re
import subprocess


def help_text() -> str:
    def _s(color: str, text: str) -> str:
        return f'<span style="color:{color};font-weight:600">{text}</span>'

    blue   = "#1e90ff"
    green  = "#10b981"
    orange = "#f97316"
    purple = "#8b5cf6"
    gray   = "#6b7280"
    cyan   = "#06b6d4"
    amber  = "#d97706"
    rose   = "#f43f5e"

    return (
        '<span style="color:#374151;font-weight:700">System Monitoring:</span>\n'
        f"  {_s(blue,'check disk')} | {_s(blue,'check memory')} | {_s(blue,'check cpu')}"
        f" | {_s(blue,'check uptime')} | {_s(blue,'check ports')}\n"
        f"  {_s(green,'top processes')} | {_s(green,'system health')}\n"
        "\n"
        '<span style="color:#374151;font-weight:700">Alerts:</span>\n'
        f"  {_s(purple,'show alerts')}"
        f'  <span style="color:#9ca3af;font-style:italic">— view recent alerts with severity and ID</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">AI-Powered Analysis:</span>\n'
        f"  {_s(green,'analyze logs: &lt;content&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— paste inline or upload a log file for AI analysis</span>\n'
        f"  {_s(green,'explain alert &lt;id&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— AI root cause analysis and fix suggestions for an alert</span>\n'
        f'  <span style="color:#9ca3af;font-style:italic">  Ask anything: "how do I reduce swap?" → answered by AI</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">Runbooks:</span>\n'
        f"  {_s(purple,'list runbooks')} | {_s(purple,'run &lt;runbook&gt;')}"
        f" | {_s(purple,'confirm &lt;runbook&gt;')} | {_s(purple,'cancel')}\n"
        "\n"
        '<span style="color:#374151;font-weight:700">Network:</span>\n'
        f"  {_s(cyan,'check ip')} | {_s(cyan,'check routes')} | {_s(cyan,'check network')}"
        f" | {_s(cyan,'check connections')}\n"
        f"  {_s(cyan,'check dns')}"
        f'  <span style="color:#9ca3af;font-style:italic">— default connectivity check</span>\n'
        f"  {_s(cyan,'check dns &lt;domain&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— full DNS lookup (A, MX, NS, TXT, CNAME)  e.g. check dns yahoo.com</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">Services:</span>\n'
        f"  {_s(amber,'show services')}"
        f'  <span style="color:#9ca3af;font-style:italic">— list all services with PID</span>\n'
        f"  {_s(amber,'show services &lt;keyword&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— filter services by name  e.g. show services ssh</span>\n'
        f"  {_s(amber,'service status &lt;name&gt;')} | {_s(amber,'restart &lt;name&gt;')}"
        f" | {_s(amber,'confirm restart &lt;name&gt;')} | {_s(amber,'check failed services')}\n"
        f"  {_s(amber,'kill process &lt;pid&gt;')} | {_s(amber,'confirm kill &lt;pid&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— terminates a process by PID (SIGTERM)</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">Multi-instance:</span>\n'
        f"  {_s(rose,'add node &lt;name&gt; &lt;user&gt;@&lt;host&gt;')} | {_s(rose,'list nodes')}"
        f" | {_s(rose,'remove node &lt;name&gt;')}\n"
        f"  {_s(rose,'&lt;any command&gt; on &lt;node&gt;')} | {_s(rose,'&lt;any command&gt; on all')}\n"
        f"  {_s(rose,'copy ssh key &lt;user&gt;@&lt;host&gt;')} | {_s(rose,'confirm copy ssh key')}\n"
        "\n"
        '<span style="color:#374151;font-weight:700">Slack &amp; Reports:</span>\n'
        f"  {_s(gray,'config set slack_webhook &lt;url&gt;')} | {_s(gray,'test slack')}"
        f" | {_s(gray,'config set alert suppress &lt;minutes&gt;')}\n"
        f"  {_s(gray,'config set report on')} | {_s(gray,'config set report off')}"
        f" | {_s(gray,'config set report hour &lt;0-23&gt;')} | {_s(gray,'show report')}\n"
        "\n"
        '<span style="color:#374151;font-weight:700">AI / LLM Config:</span>\n'
        f"  {_s(green,'test llm')}"
        f'  <span style="color:#9ca3af;font-style:italic">— verify LLM connection is working</span>\n'
        f"  {_s(green,'show llm config')}"
        f'  <span style="color:#9ca3af;font-style:italic">— show active provider, model and API key (admin only)</span>\n'

        f"  {_s(gray,'config set llm provider &lt;ollama|groq|claude|none&gt;')}\n"
        f"  {_s(gray,'config set llm api key &lt;key&gt;')} | {_s(gray,'config set llm model &lt;model&gt;')}\n"
        f"  {_s(gray,'config set ollama url &lt;url&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— default: http://localhost:11434</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">User Management (admin only):</span>\n'
        f"  {_s(rose,'add user &lt;username&gt; &lt;password&gt; &lt;viewer|operator|admin&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— roles: viewer, operator, admin</span>\n'
        f"  {_s(rose,'list users')} | {_s(rose,'show users')}"
        f'  <span style="color:#9ca3af;font-style:italic">— list all users with roles and status</span>\n'
        f"  {_s(rose,'set role &lt;username&gt; &lt;viewer|operator|admin&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— change a user\'s role</span>\n'
        f"  {_s(rose,'deactivate user &lt;username&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— disable login (user kept in DB)</span>\n'
        f"  {_s(rose,'remove user &lt;username&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— permanently delete user</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">General:</span>\n'
        f"  {_s(gray,'show system config')} | {_s(gray,'help')}\n"
        "\n"
        '<span style="color:#374151;font-weight:700">UI Only:</span>\n'
        f'  <span style="color:#7c3aed;font-weight:600;">Alert thresholds (disk / memory / cpu warning &amp; critical) are managed via the <span style="color:#4f46e5;text-decoration:underline;">Config tab</span> in the UI.</span>'
    )


def check_disk() -> dict:
    usage = shutil.disk_usage("/")
    total_gb = usage.total / (1024 ** 3)
    used_gb = usage.used / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    percent_used = (usage.used / usage.total) * 100 if usage.total else 0
    return {
        "total_gb": round(total_gb, 2),
        "used_gb": round(used_gb, 2),
        "free_gb": round(free_gb, 2),
        "percent_used": round(percent_used, 2),
    }


def _read_meminfo():
    mem = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem["MemTotal_kB"] = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem["MemAvailable_kB"] = int(line.split()[1])
                elif line.startswith("MemFree:"):
                    mem["MemFree_kB"] = int(line.split()[1])
    except Exception:
        pass
    return mem


def check_memory() -> dict:
    mem = _read_meminfo()
    total_kb = mem.get("MemTotal_kB", 0)
    avail_kb = mem.get("MemAvailable_kB") or mem.get("MemFree_kB", 0)
    used_kb = max(total_kb - avail_kb, 0)
    total_mb = int(total_kb / 1024)
    used_mb = int(used_kb / 1024)
    available_mb = int(avail_kb / 1024)
    percent_used = (used_kb / total_kb) * 100 if total_kb else 0
    return {
        "total_mb": total_mb,
        "used_mb": used_mb,
        "available_mb": available_mb,
        "percent_used": round(percent_used, 2),
    }


def check_cpu() -> dict:
    try:
        import psutil
        percent = psutil.cpu_percent(interval=0.5)
        count = psutil.cpu_count(logical=True)
        return {"percent_used": round(percent, 2), "cpu_count": count}
    except Exception:
        return {"percent_used": 0.0, "cpu_count": 0}


def check_processes(n: int = 5) -> list:
    try:
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info.get("name") or "?",
                    "cpu_pct": round(info.get("cpu_percent") or 0, 1),
                    "mem_pct": round(info.get("memory_percent") or 0, 2),
                    "status": info.get("status", "?"),
                })
            except Exception:
                pass
        procs.sort(key=lambda x: (x["cpu_pct"], x["mem_pct"]), reverse=True)
        return procs[:n]
    except Exception:
        return []


def check_uptime() -> dict:
    try:
        with open("/proc/uptime", "r") as f:
            seconds = float(f.readline().split()[0])
    except Exception:
        seconds = 0.0
    days = int(seconds // 86400)
    seconds -= days * 86400
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds = int(seconds - minutes * 60)
    return {
        "uptime_days": days,
        "uptime_hours": hours,
        "uptime_minutes": minutes,
        "uptime_seconds": seconds,
    }


def check_ports() -> list:
    try:
        res = subprocess.run(["ss", "-tuln"], capture_output=True, text=True, timeout=3)
        if res.returncode != 0:
            return []
        ports = []
        seen = set()
        for line in res.stdout.splitlines():
            for token in line.split():
                if ":" in token:
                    port_s = token.rsplit(":", 1)[-1]
                    if port_s.isdigit():
                        p = int(port_s)
                        if p not in seen:
                            seen.add(p)
                            ports.append({"port": p, "service": "unknown"})
        return ports
    except Exception:
        return []


def check_ip() -> list:
    try:
        res = subprocess.run(["ip", "-br", "addr"], capture_output=True, text=True, timeout=3)
        interfaces = []
        for line in res.stdout.splitlines():
            parts = line.split()
            if parts:
                interfaces.append({
                    "interface": parts[0],
                    "state":     parts[1] if len(parts) > 1 else "UNKNOWN",
                    "addresses": parts[2:] if len(parts) > 2 else [],
                })
        return interfaces
    except Exception:
        return []


def check_routes() -> list:
    try:
        res = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=3)
        routes = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            row = {"destination": parts[0], "gateway": "-", "interface": "-", "proto": "-", "src": "-", "metric": "-"}
            i = 1
            while i < len(parts):
                token = parts[i]
                if token == "via" and i + 1 < len(parts):
                    row["gateway"] = parts[i + 1]; i += 2
                elif token == "dev" and i + 1 < len(parts):
                    row["interface"] = parts[i + 1]; i += 2
                elif token == "proto" and i + 1 < len(parts):
                    row["proto"] = parts[i + 1]; i += 2
                elif token == "src" and i + 1 < len(parts):
                    row["src"] = parts[i + 1]; i += 2
                elif token == "metric" and i + 1 < len(parts):
                    row["metric"] = parts[i + 1]; i += 2
                else:
                    i += 1
            routes.append(row)
        return routes
    except Exception:
        return []


def check_network_stats() -> list:
    try:
        import psutil
        stats = psutil.net_io_counters(pernic=True)
        return [
            {
                "interface":     iface,
                "bytes_sent_mb": round(s.bytes_sent / (1024 ** 2), 2),
                "bytes_recv_mb": round(s.bytes_recv / (1024 ** 2), 2),
                "pkts_sent":     s.packets_sent,
                "pkts_recv":     s.packets_recv,
                "errors_in":     s.errin,
                "errors_out":    s.errout,
                "drops_in":      s.dropin,
                "drops_out":     s.dropout,
            }
            for iface, s in stats.items()
        ]
    except Exception:
        return []


def check_dns(hostnames: list[str] | None = None) -> list[dict]:
    import socket
    import time
    if hostnames is None:
        hostnames = ["google.com", "cloudflare.com", "github.com"]
    results = []
    for hostname in hostnames:
        try:
            start = time.time()
            ip = socket.gethostbyname(hostname)
            latency_ms = round((time.time() - start) * 1000, 2)
            results.append({"hostname": hostname, "resolved_ip": ip, "latency_ms": latency_ms, "status": "OK"})
        except Exception as e:
            results.append({"hostname": hostname, "resolved_ip": None, "latency_ms": None, "status": f"FAILED: {e}"})
    return results


def check_connections() -> dict:
    try:
        res = subprocess.run(["ss", "-tn"], capture_output=True, text=True, timeout=3)
        states: dict = {}
        for line in res.stdout.splitlines()[1:]:
            parts = line.split()
            if parts:
                states[parts[0]] = states.get(parts[0], 0) + 1
        return {"total": sum(states.values()), "by_state": states}
    except Exception:
        return {"total": 0, "by_state": {}}


def check_service(name: str) -> dict:
    try:
        active_res = subprocess.run(
            ["systemctl", "is-active", name], capture_output=True, text=True, timeout=3
        )
        props_res = subprocess.run(
            ["systemctl", "show", name, "--property=ActiveState,SubState,Description,MainPID"],
            capture_output=True, text=True, timeout=3,
        )
        props = {}
        for line in props_res.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v
        return {
            "name":        name,
            "active":      active_res.stdout.strip(),
            "state":       props.get("ActiveState", active_res.stdout.strip()),
            "sub_state":   props.get("SubState", ""),
            "description": props.get("Description", ""),
            "pid":         props.get("MainPID", "0"),
        }
    except Exception as e:
        return {"name": name, "active": "unknown", "state": "unknown", "error": str(e)}


def check_failed_services() -> list:
    try:
        res = subprocess.run(
            ["systemctl", "--failed", "--no-legend", "--no-pager", "--plain"],
            capture_output=True, text=True, timeout=5,
        )
        failed = []
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if parts:
                failed.append(parts[0].replace(".service", ""))
        return failed
    except Exception:
        return []


def notify_slack(webhook_url: str, metric: str, status: str, value: float, host: str = "localhost") -> bool:
    """POST a CRITICAL alert to a Slack webhook. Returns True on success."""
    import urllib.request
    import json as _json
    from datetime import datetime
    payload = {
        "text": (
            f":rotating_light: *[{status}] ChatOps Alert*\n"
            f"  *{metric.capitalize()}*: {value:.1f}% used\n"
            f"  Host: `{host}`  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    }
    try:
        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200, None
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except Exception as e:
        return False, str(e)


def generate_report(hours: int = 24) -> dict:
    """Build a health summary report for the past N hours, covering all nodes."""
    from .db import get_metric_stats, get_alert_count, list_metric_nodes
    from .nodes import list_nodes
    import socket
    from datetime import datetime

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = socket.gethostname()

    # Collect all known node names from DB + node registry
    db_nodes = set(list_metric_nodes())
    try:
        registry_nodes = set(list_nodes().keys())
    except Exception:
        registry_nodes = set()
    all_nodes = sorted(db_nodes | registry_nodes | {"local"})

    nodes = []
    for node in all_nodes:
        metrics = {}
        for m in ("disk", "memory", "cpu"):
            metrics[m] = get_metric_stats(m, hours, node=node)
        alerts = get_alert_count(hours, node=node)
        # Skip nodes with no metric data and no alerts
        has_data = any(v["samples"] > 0 for v in metrics.values()) or alerts["total"] > 0
        if not has_data:
            continue
        display_name = hostname if node == "local" else node
        nodes.append({
            "node":         node,
            "display_name": display_name,
            "metrics":      metrics,
            "alerts":       alerts,
        })

    total_alerts = get_alert_count(hours)

    return {
        "hostname":     hostname,
        "hours":        hours,
        "generated_at": generated_at,
        "nodes":        nodes,
        "total_alerts": total_alerts,
    }


def format_report_text(report: dict) -> str:
    """Format a report dict as styled HTML for the chat window."""
    hours = report["hours"]
    period = f"Last {hours}h" if hours != 24 else "Last 24h"

    def _bar(pct, color):
        w = min(int((pct or 0) / 100 * 80), 80)
        return (
            f'<span style="display:inline-block;width:{w}px;height:7px;'
            f'background:{color};border-radius:4px;vertical-align:middle;margin:0 6px"></span>'
        )

    def _metric_color(avg):
        if avg is None: return "#9ca3af"
        if avg >= 85:   return "#ef4444"
        if avg >= 70:   return "#f97316"
        return "#10b981"

    lines = [
        f'<span style="font-size:1.05rem;font-weight:700;color:#1e3a8a">&#128202; Health Report</span>'
        f'<span style="color:#6b7280;font-size:.82rem;margin-left:8px">{period} &nbsp;·&nbsp; {report["generated_at"]}</span>',
        "",
    ]

    for node_data in report.get("nodes", []):
        lines.append(
            f'<span style="color:#374151;font-weight:700;border-bottom:1px solid #e5e7eb;'
            f'display:inline-block;padding-bottom:2px;margin-top:4px">'
            f'&#128421; {node_data["display_name"]}</span>'
        )
        for metric, stats in node_data["metrics"].items():
            if stats["samples"] == 0:
                lines.append(f'  <span style="color:#9ca3af">{metric.capitalize():<8} — no data</span>')
            else:
                color = _metric_color(stats["avg"])
                bar   = _bar(stats["avg"], color)
                lines.append(
                    f'  <span style="color:#374151;font-weight:600">{metric.capitalize():<8}</span>{bar}'
                    f'<span style="color:{color};font-weight:600">{stats["avg"]:.1f}%</span>'
                    f'<span style="color:#9ca3af;font-size:.82rem"> avg &nbsp;'
                    f'&#8595;{stats["min"]:.1f}% &nbsp;&#8593;{stats["max"]:.1f}%'
                    f' &nbsp;({stats["samples"]} samples)</span>'
                )
        a = node_data["alerts"]
        if a["unacked"]:
            alert_html = (
                f'  <span style="color:#dc2626;font-weight:600">&#9888; Alerts: {a["total"]} total'
                f' &nbsp;({a["unacked"]} unacknowledged)</span>'
            )
        else:
            alert_html = (
                f'  <span style="color:#10b981">&#10003; Alerts: {a["total"]} total'
                f' &nbsp;(all acknowledged)</span>'
            )
        lines.append(alert_html)
        lines.append("")

    ta = report.get("total_alerts", {})
    if ta.get("unacked"):
        lines.append(
            f'<span style="color:#dc2626;font-weight:700">&#9888; Total alerts (all nodes): '
            f'{ta["total"]}  ({ta["unacked"]} unacknowledged)</span>'
        )
    else:
        lines.append(
            f'<span style="color:#10b981;font-weight:700">&#10003; Total alerts (all nodes): '
            f'{ta.get("total", 0)}  — all clear</span>'
        )
    return "\n".join(lines)


def format_report_slack(report: dict) -> str:
    """Format a report dict as a Slack message string."""
    hours = report["hours"]
    period = f"Last {hours}h" if hours != 24 else "Daily"
    lines = [f":bar_chart: *ChatOps {period} Report — {report['generated_at']}*", ""]

    for node_data in report.get("nodes", []):
        lines.append(f"*── {node_data['display_name']} ──*")
        for metric, stats in node_data["metrics"].items():
            if stats["samples"] == 0:
                lines.append(f"  {metric.capitalize():<8} no data")
            else:
                lines.append(
                    f"  *{metric.capitalize()}*  "
                    f"avg: {stats['avg']:.1f}%  "
                    f"peak: {stats['max']:.1f}%  "
                    f"samples: {stats['samples']}"
                )
        a = node_data["alerts"]
        flag = "  :warning:" if a["unacked"] else ""
        lines.append(f"  Alerts: *{a['total']}* total  ({a['unacked']} unacknowledged){flag}")
        lines.append("")

    ta = report.get("total_alerts", {})
    total_flag = "  :warning:" if ta.get("unacked") else ""
    lines.append(f":pushpin: Total alerts (all nodes): *{ta.get('total', 0)}*  ({ta.get('unacked', 0)} unacknowledged){total_flag}")
    return "\n".join(lines)


def analyze_logs(logs: str) -> dict:
    up = (logs or "").upper()
    errors = up.count("ERROR")
    warnings = up.count("WARNING")
    severity = "HIGH" if errors > 3 else ("MEDIUM" if errors > 0 or warnings > 0 else "LOW")
    root_cause = "Unclear root cause; requires deeper log analysis"
    if "DB" in up:
        root_cause = "Database connectivity issue"
    elif "TIMEOUT" in up:
        root_cause = "Network timeout detected"
    elif "AUTH" in up:
        root_cause = "Authentication failure detected"
    impact = "Critical" if severity == "HIGH" else ("Degraded" if severity == "MEDIUM" else "Low")
    suggested_actions = []
    if errors > 0:
        suggested_actions.append("Review error logs")
    if warnings > 0:
        suggested_actions.append("Check system health")
    if "DB" in up:
        suggested_actions.append("Inspect database connectivity/queries")
    if "TIMEOUT" in up:
        suggested_actions.append("Review network latency and timeouts")
    if "AUTH" in up:
        suggested_actions.append("Audit authentication flow and credentials")
    if not suggested_actions:
        suggested_actions.append("Monitor and collect more logs")
    return {
        "severity": severity,
        "root_cause": root_cause,
        "impact": impact,
        "suggested_actions": suggested_actions,
    }


def run_tests() -> dict:
    import subprocess
    import sys
    test_files = [
        "tests/test_chatops_actions.py",
        "tests/test_chatops_router.py",
        "tests/test_chatops_db.py",
        "tests/test_chatops_config.py",
        "tests/test_chatops_runbooks.py",
        "tests/test_chatops_api.py",
    ]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + test_files + ["--tb=short", "-v"],
            capture_output=True, text=True, timeout=180,
        )
        output = (result.stdout + result.stderr).strip()
        lines = [l for l in output.splitlines() if l.strip()]
        summary = "\n".join(lines[-10:] if len(lines) > 10 else lines)
        status = "ALL PASSED" if result.returncode == 0 else "FAILURES DETECTED"

        from datetime import datetime
        log_dir = os.path.join(os.path.dirname(__file__), "..", "sample_logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"pytest_{timestamp}.log")
        with open(log_path, "w") as f:
            f.write(output)

        return {"response": f"Test Run — {status}\n\n{summary}", "status": status}
    except subprocess.TimeoutExpired:
        return {"response": "Tests timed out after 180 seconds.", "status": "TIMEOUT"}
    except Exception as e:
        return {"response": f"Error running tests: {e}", "status": "ERROR"}


def copy_ssh_key(target: str) -> dict:
    key_path = os.path.expanduser("~/.ssh/id_rsa")
    pub_path = key_path + ".pub"

    # Generate key pair if missing
    generated = False
    if not os.path.exists(key_path):
        try:
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", ""],
                capture_output=True, text=True, timeout=10, check=True,
            )
            generated = True
        except Exception as e:
            return {"status": "error", "message": f"Failed to generate SSH key: {e}"}

    try:
        result = subprocess.run(
            ["ssh-copy-id", "-i", pub_path, "-o", "StrictHostKeyChecking=no", target],
            capture_output=True, text=True, timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            msg = ("SSH key generated and copied" if generated else "SSH key copied") + f" to {target}."
            return {"status": "ok", "message": msg}
        # Password prompt or auth failure — give actionable output
        if "password:" in output.lower() or "Permission denied" in output:
            return {
                "status": "error",
                "message": (
                    f"Remote host requires a password for initial key copy.\n"
                    f"Run this in your terminal:\n"
                    f"  ssh-copy-id -i {pub_path} {target}"
                ),
            }
        return {"status": "error", "message": output or "ssh-copy-id failed."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Timed out waiting for ssh-copy-id (30s). The host may be unreachable or waiting for a password."}
    except FileNotFoundError:
        return {"status": "error", "message": "ssh-copy-id not found. Install openssh-client and retry."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def alert_status(percent: float, warning: float = 80.0, critical: float = 90.0) -> str:
    if percent >= critical:
        return "CRITICAL"
    if percent >= warning:
        return "WARNING"
    return "OK"
