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
    resp = _resp("config")
    assert "Disk" in resp and "Warning" in resp


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


# ── Network commands ──────────────────────────────────────────────────────────

def test_route_check_ip():
    assert "interface" in _resp("check ip").lower() or "network" in _resp("check ip").lower()


def test_route_check_routes():
    resp = _resp("check routes")
    assert "destination" in resp.lower() or "route" in resp.lower()


def test_route_check_network():
    resp = _resp("check network")
    assert "network" in resp.lower() or "bytes" in resp.lower() or "interface" in resp.lower()


def test_route_check_dns():
    resp = _resp("check dns")
    assert "google.com" in resp.lower() or "dns" in resp.lower()


def test_route_check_connections():
    resp = _resp("check connections")
    assert "connection" in resp.lower()


# ── Service commands ──────────────────────────────────────────────────────────

def test_route_service_status():
    resp = _resp("service status ssh")
    assert "ssh" in resp.lower()


def test_route_restart_requires_confirmation():
    resp = _resp("restart nginx")
    assert "confirm" in resp.lower()


def test_route_confirm_restart_without_pending():
    resp = _resp("confirm restart nonexistentservice_xyz")
    assert resp  # returns some response (error or failed)


def test_route_check_failed_services():
    resp = _resp("check failed services")
    assert "failed" in resp.lower() or "service" in resp.lower()


# ── Multi-node commands ───────────────────────────────────────────────────────

def test_route_list_nodes():
    resp = _resp("list nodes")
    assert "local" in resp.lower() or "node" in resp.lower()


def test_route_add_node():
    resp = _resp("add node testnode ubuntu@1.2.3.4")
    assert "testnode" in resp.lower() or "added" in resp.lower()
    # cleanup
    route_message("remove node testnode")


def test_route_remove_node_unknown():
    resp = _resp("remove node nonexistent_xyz")
    assert "not found" in resp.lower() or "nonexistent" in resp.lower()


def test_route_show_alerts_on_node():
    resp = _resp("show alerts on local")
    assert "alert" in resp.lower()


# ── Slack & report commands ───────────────────────────────────────────────────

def test_route_config_set_slack_webhook():
    resp = _resp("config set slack_webhook https://hooks.slack.com/test/ABC123")
    assert "configured" in resp.lower() or "webhook" in resp.lower()


def test_route_config_set_alert_suppress():
    resp = _resp("config set alert suppress 20")
    assert "20" in resp or "suppress" in resp.lower()


def test_route_config_set_report_on():
    resp = _resp("config set report on")
    assert "enabled" in resp.lower()


def test_route_config_set_report_off():
    resp = _resp("config set report off")
    assert "disabled" in resp.lower()


def test_route_config_set_report_hour():
    resp = _resp("config set report hour 9")
    assert "09:00" in resp or "enabled" in resp.lower()


def test_route_show_report():
    resp = _resp("show report")
    assert "health report" in resp.lower() or "report" in resp.lower()
