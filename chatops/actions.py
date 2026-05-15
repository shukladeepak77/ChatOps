import shutil
import os
import re
import subprocess
import threading

_test_lock = threading.Lock()
_test_running = False


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
        '<span style="color:#374151;font-weight:700">General:</span>\n'
        f"  {_s(gray,'show system config')} | {_s(gray,'date')} | {_s(gray,'help')}\n"
        f"  {_s(gray,'show predictive alerts')}"
        f'  <span style="color:#9ca3af;font-style:italic">— metrics trending toward threshold breach</span>\n'
        f"  {_s(gray,'run tests')} | {_s(gray,'show test logs')}"
        f'  <span style="color:#9ca3af;font-style:italic">— run test suite / list past runs (developer+ only)</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">Alerts:</span>\n'
        f"  {_s(purple,'show alerts')} | {_s(purple,'show predictive alerts')}"
        f'  <span style="color:#9ca3af;font-style:italic">— recent alerts / metrics trending toward threshold</span>\n'
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
        f"  {_s(purple,'dry run &lt;runbook&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— simulate without executing (safe preview)</span>\n'
        f'  <span style="color:#9ca3af;font-style:italic">  Available: clear_tmp, disk_breakdown, large_logs, listening_services, flush_cache, rotate_logs, rotate_secret</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">Knowledge Base:</span>\n'
        f"  {_s(cyan,'list kb')}"
        f'  <span style="color:#9ca3af;font-style:italic">— list all KB articles</span>\n'
        f"  {_s(cyan,'add kb &lt;title&gt;: &lt;content&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— add a new article</span>\n'
        f"  {_s(cyan,'show kb &lt;id&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— read full article</span>\n'
        f"  {_s(cyan,'search kb &lt;keyword&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— search by title, content or tags</span>\n'
        f"  {_s(cyan,'delete kb &lt;id&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— delete article (admin only)</span>\n'
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
        '<span style="color:#374151;font-weight:700">Analytics:</span>\n'
        f"  {_s(green,'show analytics')}"
        f'  <span style="color:#9ca3af;font-style:italic">— alert stats, MTTR, top commands (last 7 days)</span>\n'
        f"  {_s(green,'show analytics &lt;N&gt;d')}"
        f'  <span style="color:#9ca3af;font-style:italic">— e.g. show analytics 30d</span>\n'
        f"  {_s(green,'show prometheus metrics')}"
        f'  <span style="color:#9ca3af;font-style:italic">— Prometheus-format metrics inline</span>\n'
        f"  {_s(green,'configure prometheus')}"
        f'  <span style="color:#9ca3af;font-style:italic">— enable/disable individual metrics</span>\n'
        f"  {_s(green,'analyze prometheus')}"
        f'  <span style="color:#9ca3af;font-style:italic">— AI interpretation and action recommendations</span>\n'
        f"  {_s(green,'download PDF')}"
        f'  <span style="color:#9ca3af;font-style:italic">— GET /chatops/analytics/report.pdf</span>\n'
        "\n"
        '<span style="color:#374151;font-weight:700">Slack &amp; Reports:</span>\n'
        f"  {_s(gray,'config set slack_webhook &lt;url&gt;')} | {_s(gray,'test slack')}"
        f" | {_s(gray,'config set alert suppress &lt;minutes&gt;')}\n"
        f"  {_s(gray,'config set slack bot token &lt;token&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— enable inbound Slack commands</span>\n'
        f"  {_s(gray,'config set slack signing secret &lt;secret&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— verify Slack request signatures</span>\n'
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
        f"  {_s(rose,'add user &lt;username&gt; &lt;password&gt; &lt;viewer|operator|developer|admin&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— roles: viewer &lt; operator &lt; developer &lt; admin</span>\n'
        f"  {_s(rose,'list users')} | {_s(rose,'show users')}"
        f'  <span style="color:#9ca3af;font-style:italic">— list all users with roles and status</span>\n'
        f"  {_s(rose,'set role &lt;username&gt; &lt;viewer|operator|developer|admin&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— change a user\'s role</span>\n'
        f"  {_s(rose,'deactivate user &lt;username&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— disable login (user kept in DB)</span>\n'
        f"  {_s(rose,'remove user &lt;username&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— permanently delete user</span>\n'
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
    global _test_running
    import sys
    from datetime import datetime

    with _test_lock:
        if _test_running:
            return {"response": "A test run is already in progress. Use `show test logs` to check for results when it completes."}
        _test_running = True

    test_files = [
        "tests/test_chatops_actions.py",
        "tests/test_chatops_router.py",
        "tests/test_chatops_db.py",
        "tests/test_chatops_config.py",
        "tests/test_chatops_runbooks.py",
        "tests/test_chatops_api.py",
        "tests/test_chatops_analytics.py",
        "tests/test_chatops_kb.py",
        "tests/test_chatops_auth.py",
    ]

    started_at = datetime.now()
    started_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    log_filename = f"pytest_{timestamp}.log"
    log_dir = os.path.join(os.path.dirname(__file__), "..", "sample_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    def _run_in_background():
        global _test_running
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + test_files + ["--tb=short", "-v"],
                capture_output=True, text=True, timeout=1200,
            )
            finished_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            output = (result.stdout + result.stderr).strip()
            status = "ALL PASSED" if result.returncode == 0 else "FAILURES DETECTED"
            header = (
                f"{'='*60}\n"
                f"  ChatOps Test Run\n"
                f"  Started:  {started_str}\n"
                f"  Finished: {finished_str}\n"
                f"  Status:   {status}\n"
                f"{'='*60}\n\n"
            )
            with open(log_path, "w") as f:
                f.write(header + output)
        except subprocess.TimeoutExpired:
            with open(log_path, "w") as f:
                f.write(f"Test run timed out after 20 minutes. Started: {started_str}\n")
        except Exception as e:
            with open(log_path, "w") as f:
                f.write(f"Error running tests: {e}\nStarted: {started_str}\n")
        finally:
            global _test_running
            _test_running = False

    thread = threading.Thread(target=_run_in_background, daemon=True)
    thread.start()

    return {
        "response": (
            f"Test run started at {started_str}.\n\n"
            f"Tests take ~12 minutes to complete. Use `show test logs` to see results when done.\n\n"
            f"📄 Log will be saved as: {log_filename}"
        ),
        "status": "RUNNING",
    }


# All available Prometheus metric keys (used for config validation)
PROMETHEUS_METRIC_KEYS = [
    "alerts_by_severity",
    "alerts_unacked",
    "mttr",
    "system_usage",
    "top_commands",
    "runbooks_executed",
    "kb_articles",
    "audit_events_24h",
]

_PROM_DEFAULTS = {k: True for k in PROMETHEUS_METRIC_KEYS}


def _enabled_prometheus_metrics() -> dict:
    from chatops.config import load_config
    cfg = load_config()
    stored = cfg.get("prometheus_metrics", {})
    return {**_PROM_DEFAULTS, **stored}


def get_prometheus_metrics() -> dict:
    from chatops.db import unacked_count, kb_list, get_audit_log, _conn as _db_conn
    from chatops.analytics import get_alert_stats, get_mttr_stats, get_command_stats
    import time

    enabled = _enabled_prometheus_metrics()
    lines = ["```"]

    if enabled.get("alerts_by_severity"):
        stats = get_alert_stats(7)
        lines += [
            "# HELP chatops_alerts_total Total alerts by severity (last 7d)",
            "# TYPE chatops_alerts_total gauge",
        ]
        for sev, cnt in stats.get("by_severity", {}).items():
            lines.append(f'chatops_alerts_total{{severity="{sev}"}} {cnt}')
        lines.append("")

    if enabled.get("alerts_unacked"):
        lines += [
            "# HELP chatops_alerts_unacked Unacknowledged alerts",
            "# TYPE chatops_alerts_unacked gauge",
            f"chatops_alerts_unacked {unacked_count()}",
            "",
        ]

    if enabled.get("mttr"):
        mttr = get_mttr_stats(7)
        lines += [
            "# HELP chatops_mttr_minutes_avg Average MTTR in minutes (last 7d)",
            "# TYPE chatops_mttr_minutes_avg gauge",
            f"chatops_mttr_minutes_avg {mttr['avg_minutes'] if mttr['avg_minutes'] is not None else 'NaN'}",
            "",
        ]

    if enabled.get("system_usage"):
        disk = check_disk()
        mem = check_memory()
        cpu = check_cpu()
        lines += [
            "# HELP chatops_system_usage_percent Current resource usage %",
            "# TYPE chatops_system_usage_percent gauge",
            f'chatops_system_usage_percent{{resource="disk"}}   {disk.get("percent_used", "N/A")}',
            f'chatops_system_usage_percent{{resource="memory"}} {mem.get("percent_used", "N/A")}',
            f'chatops_system_usage_percent{{resource="cpu"}}    {cpu.get("percent_used", "N/A")}',
            "",
        ]

    if enabled.get("top_commands"):
        top_cmds = get_command_stats(7)[:5]
        if top_cmds:
            lines += [
                "# HELP chatops_top_commands_total Command usage count (last 7d)",
                "# TYPE chatops_top_commands_total gauge",
            ]
            for cmd in top_cmds:
                safe = cmd["command"].replace('"', '\\"')
                lines.append(f'chatops_top_commands_total{{command="{safe}"}} {cmd["count"]}')
            lines.append("")

    if enabled.get("runbooks_executed"):
        try:
            with _db_conn() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE command LIKE '%runbook%' OR command LIKE 'confirm %'"
                ).fetchone()[0]
        except Exception:
            count = 0
        lines += [
            "# HELP chatops_runbooks_executed_total Total runbooks executed (all time)",
            "# TYPE chatops_runbooks_executed_total counter",
            f"chatops_runbooks_executed_total {count}",
            "",
        ]

    if enabled.get("kb_articles"):
        try:
            kb_count = len(kb_list(limit=9999))
        except Exception:
            kb_count = 0
        lines += [
            "# HELP chatops_kb_articles_total Total Knowledge Base articles",
            "# TYPE chatops_kb_articles_total gauge",
            f"chatops_kb_articles_total {kb_count}",
            "",
        ]

    if enabled.get("audit_events_24h"):
        try:
            from datetime import datetime, timedelta, timezone
            since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            with _db_conn() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?", (since,)
                ).fetchone()[0]
        except Exception:
            count = 0
        lines += [
            "# HELP chatops_audit_events_24h Audit log events in the last 24 hours",
            "# TYPE chatops_audit_events_24h gauge",
            f"chatops_audit_events_24h {count}",
            "",
        ]

    lines += [f"# Generated at {int(time.time())}", "```"]
    raw = "\n".join(lines)
    return {"response": raw, "prometheus_output": raw}


def configure_prometheus_metrics() -> dict:
    enabled = _enabled_prometheus_metrics()
    lines = ["**Prometheus Metric Configuration**\n"]
    lines.append("Use `enable metric <name>` or `disable metric <name>` to toggle.\n")
    for key in PROMETHEUS_METRIC_KEYS:
        status = "✅ enabled" if enabled.get(key) else "❌ disabled"
        lines.append(f"  `{key}` — {status}")
    return {"response": "\n".join(lines)}


def toggle_prometheus_metric(name: str, enable: bool) -> dict:
    from chatops.config import load_config, save_config
    if name not in PROMETHEUS_METRIC_KEYS:
        keys = ", ".join(f"`{k}`" for k in PROMETHEUS_METRIC_KEYS)
        return {"response": f"Unknown metric key `{name}`. Valid keys: {keys}"}
    cfg = load_config()
    stored = cfg.get("prometheus_metrics", {})
    stored[name] = enable
    save_config({"prometheus_metrics": stored})
    state = "enabled" if enable else "disabled"
    return {"response": f"Metric `{name}` is now **{state}**. Type `configure prometheus` to see full list."}


def analyze_prometheus_metrics(metrics_text: str) -> dict:
    from chatops.config import load_config
    from chatops.llm import ask
    cfg = load_config()
    if cfg.get("llm_provider", "none") == "none":
        return {"response": "LLM is not configured. Set a provider in system config to use AI analysis."}

    system_prompt = (
        "You are a senior site reliability engineer reviewing Prometheus metrics from a ChatOps platform. "
        "Analyse the metrics provided and give a concise, actionable report covering:\n"
        "1. Health summary — what looks good and what is concerning\n"
        "2. Any metrics in WARNING or CRITICAL territory (high unacked alerts, high MTTR, resource usage above 80%)\n"
        "3. Specific recommended actions the ops team should take right now\n"
        "Keep the response under 300 words. Use bullet points."
    )
    analysis = ask(
        prompt=f"Here are the current Prometheus metrics:\n\n{metrics_text}",
        system=system_prompt,
    )
    if analysis.startswith("["):
        return {"response": f"AI analysis failed: {analysis}"}
    return {"response": f"**🤖 AI Analysis of Prometheus Metrics**\n\n{analysis}"}


def analyze_test_log(filename: str) -> dict:
    import re
    log_dir = os.path.join(os.path.dirname(__file__), "..", "sample_logs")
    log_path = os.path.join(log_dir, filename)
    if not re.fullmatch(r"pytest_\d{8}_\d{6}\.log", filename):
        return {"response": "Invalid log filename."}
    if not os.path.isfile(log_path):
        return {"response": f"Log file not found: {filename}"}

    with open(log_path) as f:
        content = f.read()

    # Send at most ~6000 chars to stay within LLM token budget
    truncated = content[-6000:] if len(content) > 6000 else content

    from .llm import ask as _llm_ask, is_configured as _llm_ok
    if not _llm_ok():
        # Rule-based fallback
        passed = len(re.findall(r" PASSED", content))
        failed = len(re.findall(r" FAILED", content))
        errors = re.findall(r"^FAILED (.+)$", content, re.MULTILINE)
        lines = [f"Test Log Analysis — {filename}",
                 f"Passed: {passed}  |  Failed: {failed}"]
        if errors:
            lines.append("\nFailed tests:")
            lines.extend(f"  • {e}" for e in errors[:10])
        lines.append("\n(Enable LLM for AI-powered insights)")
        return {"response": "\n".join(lines)}

    prompt = (
        f"Analyse this pytest log and provide:\n"
        f"1. A one-line overall health summary\n"
        f"2. List of failed tests with likely root cause (if any)\n"
        f"3. Any patterns or recurring issues\n"
        f"4. Actionable fix suggestions\n\n"
        f"Log ({filename}):\n{truncated}"
    )
    answer = _llm_ask(prompt, system=(
        "You are a senior QA engineer. Be concise and practical. "
        "Format output with clear sections. No filler text."
    ))
    return {"response": f"🤖 AI Test Log Analysis — {filename}\n\n{answer}"}


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
