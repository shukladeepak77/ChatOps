from chatops.actions import (
    check_disk, check_memory, check_cpu, check_processes,
    check_uptime, check_ports, alert_status, analyze_logs,
)


# ── Disk ──────────────────────────────────────────────────────────────────────

def test_check_disk_returns_keys():
    result = check_disk()
    assert all(k in result for k in ["total_gb", "used_gb", "free_gb", "percent_used"])


def test_check_disk_percent_range():
    assert 0 <= check_disk()["percent_used"] <= 100


# ── Memory ────────────────────────────────────────────────────────────────────

def test_check_memory_returns_keys():
    result = check_memory()
    assert all(k in result for k in ["total_mb", "used_mb", "available_mb", "percent_used"])


def test_check_memory_percent_range():
    assert 0 <= check_memory()["percent_used"] <= 100


# ── CPU ───────────────────────────────────────────────────────────────────────

def test_check_cpu_returns_keys():
    result = check_cpu()
    assert all(k in result for k in ["percent_used", "cpu_count"])


def test_check_cpu_percent_range():
    assert 0 <= check_cpu()["percent_used"] <= 100


def test_check_cpu_count_positive():
    assert check_cpu()["cpu_count"] >= 1


# ── Processes ─────────────────────────────────────────────────────────────────

def test_check_processes_returns_list():
    assert isinstance(check_processes(), list)


def test_check_processes_has_fields():
    procs = check_processes()
    if procs:
        assert all(k in procs[0] for k in ["pid", "name", "cpu_pct", "mem_pct"])


def test_check_processes_limit():
    assert len(check_processes(n=3)) <= 3


# ── Uptime ────────────────────────────────────────────────────────────────────

def test_check_uptime_returns_keys():
    result = check_uptime()
    assert all(k in result for k in ["uptime_days", "uptime_hours", "uptime_minutes"])


def test_check_uptime_values_non_negative():
    result = check_uptime()
    assert result["uptime_days"] >= 0
    assert result["uptime_hours"] >= 0
    assert result["uptime_minutes"] >= 0


# ── Ports ─────────────────────────────────────────────────────────────────────

def test_check_ports_returns_list():
    assert isinstance(check_ports(), list)


# ── Alert status ──────────────────────────────────────────────────────────────

def test_alert_status_ok():
    assert alert_status(50) == "OK"


def test_alert_status_warning():
    assert alert_status(82) == "WARNING"


def test_alert_status_critical():
    assert alert_status(92) == "CRITICAL"


def test_alert_status_custom_thresholds():
    assert alert_status(75, warning=70, critical=90) == "WARNING"


# ── Log analysis ──────────────────────────────────────────────────────────────

def test_analyze_logs_high_severity():
    logs = "\n".join(["ERROR: fail"] * 5)
    assert analyze_logs(logs)["severity"] == "HIGH"


def test_analyze_logs_medium_severity():
    assert analyze_logs("WARNING: slow response\nINFO: started")["severity"] == "MEDIUM"


def test_analyze_logs_low_severity():
    assert analyze_logs("INFO: all good\nINFO: started")["severity"] == "LOW"


def test_analyze_logs_db_root_cause():
    assert "Database" in analyze_logs("ERROR: DB connection refused")["root_cause"]


def test_analyze_logs_timeout_root_cause():
    assert "timeout" in analyze_logs("ERROR: TIMEOUT waiting")["root_cause"].lower()


def test_analyze_logs_auth_root_cause():
    assert "Authentication" in analyze_logs("ERROR: AUTH token expired")["root_cause"]
