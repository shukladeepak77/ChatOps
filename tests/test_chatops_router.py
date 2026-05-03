from chatops.router import route_message


def _resp(msg):
    return route_message(msg).get("response", "")


# ── Disk ──────────────────────────────────────────────────────────────────────

def test_route_disk_exact():
    assert "Disk" in _resp("check disk")


def test_route_disk_natural():
    assert "Disk" in _resp("how full is my disk")


# ── Memory ────────────────────────────────────────────────────────────────────

def test_route_memory_exact():
    assert "Memory" in _resp("check memory")


def test_route_memory_natural():
    assert "Memory" in _resp("how much ram am i using")


# ── CPU ───────────────────────────────────────────────────────────────────────

def test_route_cpu_exact():
    assert "CPU" in _resp("check cpu")


def test_route_cpu_natural():
    assert "CPU" in _resp("whats my cpu load")


# ── Uptime ────────────────────────────────────────────────────────────────────

def test_route_uptime_exact():
    assert "Uptime" in _resp("check uptime")


def test_route_uptime_natural():
    assert "Uptime" in _resp("how long has the server been up")


# ── Ports ─────────────────────────────────────────────────────────────────────

def test_route_ports():
    assert "port" in _resp("what ports are open").lower()


# ── Processes ─────────────────────────────────────────────────────────────────

def test_route_processes_exact():
    assert "process" in _resp("top processes").lower()


def test_route_processes_natural():
    assert "process" in _resp("what processes are hogging memory").lower()


# ── Health ────────────────────────────────────────────────────────────────────

def test_route_health_summary():
    assert "overall_status" in route_message("system health")


def test_route_health_has_all_metrics():
    resp = _resp("system health")
    for metric in ["Disk", "Memory", "CPU", "Uptime"]:
        assert metric in resp


# ── Alerts ────────────────────────────────────────────────────────────────────

def test_route_alerts():
    assert "alert" in _resp("show alerts").lower()


# ── Runbooks ──────────────────────────────────────────────────────────────────

def test_route_runbooks_list():
    assert "run " in _resp("list runbooks")


# ── Config ────────────────────────────────────────────────────────────────────

def test_route_config():
    assert "disk_warning" in _resp("config")


# ── Inline log analysis ───────────────────────────────────────────────────────

def test_route_inline_log_analysis():
    assert "Severity" in _resp("analyze logs: ERROR db connection failed")


# ── Runbook flow ──────────────────────────────────────────────────────────────

def test_route_runbook_run_request():
    assert "confirm" in _resp("run clear_tmp").lower()


def test_route_runbook_confirm_without_run():
    resp = _resp("confirm clear_tmp")
    assert "error" in resp.lower() or "No pending" in resp


def test_route_runbook_cancel():
    route_message("run clear_tmp")
    assert "Cancelled" in _resp("cancel")


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_route_unknown_message():
    resp = _resp("xyzzy nonsense blah")
    assert "understand" in resp.lower() or "didn't" in resp.lower()


def test_route_empty_message():
    resp = _resp("")
    assert "help" in resp.lower() or "Commands" in resp


def test_route_help():
    resp = _resp("help")
    assert "check disk" in resp.lower() or "Commands" in resp


def test_route_case_insensitive():
    assert "Disk" in _resp("CHECK DISK")


def test_route_punctuation_stripped():
    assert "Disk" in _resp("check disk!")
