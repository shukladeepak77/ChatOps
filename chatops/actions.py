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

    return (
        '<span style="color:#374151;font-weight:700">Commands:</span>\n'
        f"  {_s(blue,'check disk')} | {_s(blue,'check memory')} | {_s(blue,'check cpu')}"
        f" | {_s(blue,'check uptime')} | {_s(blue,'check ports')}\n"
        f"  {_s(green,'top processes')} | {_s(green,'system health')}\n"
        f"  {_s(orange,'analyze logs: &lt;content&gt;')}"
        f'  <span style="color:#9ca3af;font-style:italic">— paste inline, or upload a log file</span>\n'
        f"  {_s(purple,'show alerts')} | {_s(purple,'list runbooks')}"
        f" | {_s(purple,'run &lt;runbook&gt;')} | {_s(purple,'confirm &lt;runbook&gt;')} | {_s(purple,'cancel')}\n"
        f"  {_s(gray,'run tests')} | {_s(gray,'config')} | {_s(gray,'help')}"
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


def alert_status(percent: float, warning: float = 80.0, critical: float = 90.0) -> str:
    if percent >= critical:
        return "CRITICAL"
    if percent >= warning:
        return "WARNING"
    return "OK"
