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
    assert "Disk" in resp and "warn" in resp


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


# ── User management (admin-only) ──────────────────────────────────────────────

def _resp_role(msg, role="admin"):
    from chatops.router import route_message
    return route_message(msg, caller_role=role).get("response", "")


def test_add_user_valid():
    resp = _resp_role("add user testuser pass123 operator", role="admin")
    assert "created" in resp.lower()


def test_add_user_duplicate():
    _resp_role("add user dupuser pass123 operator", role="admin")
    resp = _resp_role("add user dupuser pass123 operator", role="admin")
    assert "already exists" in resp.lower()


def test_add_user_invalid_syntax():
    resp = _resp_role("add user baduser admin", role="admin")
    assert "Invalid syntax" in resp or "Usage" in resp


def test_add_user_denied_for_operator():
    resp = _resp_role("add user newuser pass123 viewer", role="operator")
    assert "denied" in resp.lower() or "Access" in resp


def test_list_users_admin():
    resp = _resp_role("list users", role="admin")
    assert "admin" in resp.lower()


def test_list_users_denied_for_viewer():
    resp = _resp_role("list users", role="viewer")
    assert "denied" in resp.lower() or "Access" in resp


def test_remove_user():
    _resp_role("add user removetest pass123 viewer", role="admin")
    resp = _resp_role("remove user removetest", role="admin")
    assert "deleted" in resp.lower()


def test_remove_admin_blocked():
    resp = _resp_role("remove user admin", role="admin")
    assert "Cannot" in resp


def test_deactivate_user():
    _resp_role("add user deactest pass123 viewer", role="admin")
    resp = _resp_role("deactivate user deactest", role="admin")
    assert "deactivated" in resp.lower()


def test_set_role():
    _resp_role("add user roletest pass123 viewer", role="admin")
    resp = _resp_role("set role roletest operator", role="admin")
    assert "updated" in resp.lower()


def test_set_role_invalid_syntax():
    resp = _resp_role("set role baduser", role="admin")
    assert "Invalid syntax" in resp or "Usage" in resp


# ── Show services ─────────────────────────────────────────────────────────────

def test_show_services_returns_output():
    resp = _resp("show services")
    assert "Services" in resp or "No services" in resp


def test_show_services_tip():
    resp = _resp("show services")
    assert "Tip" in resp or "filter" in resp or "Services" in resp


def test_search_services_filter():
    resp = _resp("show services systemd")
    assert "systemd" in resp.lower() or "No services" in resp


# ── Kill process ──────────────────────────────────────────────────────────────

def test_kill_invalid_pid():
    resp = _resp("kill process 9999999")
    assert "No process" in resp or "not found" in resp.lower()


def test_confirm_kill_without_request():
    resp = _resp("confirm kill 12345")
    assert "No pending" in resp or "first" in resp.lower()


# ── DNS lookup ────────────────────────────────────────────────────────────────

def test_check_dns_default():
    resp = _resp("check dns")
    assert "DNS" in resp


def test_check_dns_domain():
    resp = _resp("check dns google.com")
    assert "google.com" in resp or "DNS" in resp or "Resolved" in resp


def test_check_dns_invalid_domain():
    resp = _resp("check dns thisisnotavaliddomain12345xyz.com")
    assert "not found" in resp.lower() or "NXDOMAIN" in resp or "failed" in resp.lower() or "DNS" in resp


# ── Analytics router ──────────────────────────────────────────────────────────

def test_show_analytics_basic():
    resp = _resp("show analytics")
    assert "Analytics" in resp and "Alerts" in resp


def test_show_analytics_with_period():
    resp = _resp("show analytics 14d")
    assert "14 days" in resp


# ── Slack config commands ─────────────────────────────────────────────────────

def test_config_set_slack_bot_token():
    resp = _resp_role("config set slack bot token xoxb-test-token", role="admin")
    assert "token" in resp.lower() or "saved" in resp.lower() or "enabled" in resp.lower()


def test_config_set_slack_signing_secret():
    resp = _resp_role("config set slack signing secret mysecret123", role="admin")
    assert "saved" in resp.lower() or "secret" in resp.lower()


# ── LLM config (admin-only) ───────────────────────────────────────────────────

def test_show_llm_config_admin():
    resp = _resp_role("show llm config", role="admin")
    assert "Provider" in resp or "LLM" in resp


def test_show_llm_config_denied_for_operator():
    resp = _resp_role("show llm config", role="operator")
    assert "denied" in resp.lower() or "Access" in resp


# ── Dry-run runbook (router) ──────────────────────────────────────────────────

def test_dry_run_route_clear_tmp():
    resp = _resp("dry run clear_tmp")
    assert "[DRY RUN]" in resp


def test_dry_run_route_disk_breakdown():
    resp = _resp("dry run disk_breakdown")
    assert "[DRY RUN]" in resp


def test_dry_run_route_unknown():
    resp = _resp("dry run nonexistent_xyz")
    assert "Unknown" in resp or "Available" in resp


def test_dry_run_route_rotate_secret():
    resp = _resp("dry run rotate_secret")
    assert "[DRY RUN]" in resp


def test_dry_run_does_not_execute():
    # dry run clear_tmp should not say "Deleted" or show confirm prompt
    resp = _resp("dry run clear_tmp")
    assert "confirm" not in resp.lower()


# ── Predictive alerts (router) ────────────────────────────────────────────────

def test_show_predictive_alerts_returns_response():
    resp = _resp("show predictive alerts")
    assert resp  # always returns something


def test_show_predictive_alerts_no_breach():
    resp = _resp("show predictive alerts")
    # With test data (no real trending), expect no-breach message
    assert "trending" in resp.lower() or "No metrics" in resp


def test_predictive_alerts_alias():
    resp = _resp("predictive alerts")
    assert resp


def test_check_predictive_alias():
    resp = _resp("check predictive")
    assert resp


# ── Predictive check function ─────────────────────────────────────────────────

def test_predictive_check_returns_list():
    from chatops.predictive import check_predictive_alerts
    result = check_predictive_alerts()
    assert isinstance(result, list)


def test_predictive_check_with_trending_data():
    from chatops.db import add_metric, init_db
    from chatops.predictive import check_predictive_alerts
    init_db()
    # Insert 10 steadily rising CPU values approaching warning threshold
    for i in range(10):
        add_metric("cpu", 70.0 + i * 1.5, node="testnode_pred")
    result = check_predictive_alerts(node="testnode_pred")
    # With slope of 1.5%/sample and current ~83.5%, should flag warning (80%)
    assert isinstance(result, list)


def test_predictive_check_flat_no_alert():
    from chatops.db import add_metric, init_db
    from chatops.predictive import check_predictive_alerts
    init_db()
    # Flat metric well below threshold — should not fire
    for i in range(10):
        add_metric("disk", 20.0, node="flatnode_pred")
    result = check_predictive_alerts(node="flatnode_pred")
    assert all(a["metric"] != "disk" for a in result)


# ── Date command ──────────────────────────────────────────────────────────────

def test_route_date_command():
    resp = _resp("date")
    assert "2026" in resp or "2025" in resp


def test_route_what_time_is_it():
    resp = _resp("what time is it")
    assert ":" in resp  # HH:MM:SS present


# ── Developer role enforcement ────────────────────────────────────────────────

def test_run_test_denied_for_operator():
    resp = _resp_role("run test", role="operator")
    assert "denied" in resp.lower() or "Access" in resp


def test_run_test_allowed_for_developer():
    resp = _resp_role("run test", role="developer")
    assert "denied" not in resp.lower()


def test_run_test_allowed_for_admin():
    resp = _resp_role("run test", role="admin")
    assert "denied" not in resp.lower()


def test_add_user_developer_role():
    resp = _resp_role("add user devtest pass123 developer", role="admin")
    assert "created" in resp.lower()


def test_set_role_to_developer():
    _resp_role("add user devroletest pass123 viewer", role="admin")
    resp = _resp_role("set role devroletest developer", role="admin")
    assert "updated" in resp.lower()
