import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    async def _noop():
        pass
    import app as app_module
    monkeypatch.setattr(app_module, "_health_check_loop", _noop)
    monkeypatch.setattr(app_module, "_daily_report_loop", _noop)
    from app import app
    with TestClient(app) as c:
        resp = c.post("/chatops/auth/login", json={"username": "admin", "password": "admin"})
        token = resp.json()["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


# ── Page ──────────────────────────────────────────────────────────────────────

def test_chatops_page_loads(client):
    resp = client.get("/chatops")
    assert resp.status_code == 200
    assert "ChatOps Console" in resp.text


# ── Messages ──────────────────────────────────────────────────────────────────

def test_message_disk(client):
    resp = client.post("/chatops/message", json={"message": "check disk"})
    assert resp.status_code == 200
    assert "Disk" in resp.json()["response"]


def test_message_memory(client):
    resp = client.post("/chatops/message", json={"message": "check memory"})
    assert resp.status_code == 200
    assert "Memory" in resp.json()["response"]


def test_message_cpu(client):
    resp = client.post("/chatops/message", json={"message": "check cpu"})
    assert resp.status_code == 200
    assert "CPU" in resp.json()["response"]


def test_message_health(client):
    resp = client.post("/chatops/message", json={"message": "system health"})
    assert resp.status_code == 200
    assert "overall_status" in resp.json()


def test_message_processes(client):
    resp = client.post("/chatops/message", json={"message": "top processes"})
    assert resp.status_code == 200
    assert "process" in resp.json()["response"].lower()


def test_message_unknown(client):
    resp = client.post("/chatops/message", json={"message": "xyzzy blah nonsense"})
    assert resp.status_code == 200
    assert resp.json()["response"]


# ── History ───────────────────────────────────────────────────────────────────

def test_history_get(client):
    resp = client.get("/chatops/history")
    assert resp.status_code == 200
    assert isinstance(resp.json()["history"], list)


def test_history_persists_messages(client):
    client.delete("/chatops/history")
    client.post("/chatops/message", json={"message": "check disk"})
    messages = [m["message"] for m in client.get("/chatops/history").json()["history"]]
    assert "check disk" in messages


def test_history_clear(client):
    client.post("/chatops/message", json={"message": "check disk"})
    client.delete("/chatops/history")
    assert client.get("/chatops/history").json()["history"] == []


# ── Alerts ────────────────────────────────────────────────────────────────────

def test_alerts_get(client):
    resp = client.get("/chatops/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["alerts"], list)
    assert isinstance(data["unacked_count"], int)


def test_alerts_ack(client):
    from chatops.db import add_alert
    alert_id = add_alert("Test alert", "WARNING")
    assert client.post(f"/chatops/alerts/{alert_id}/ack").status_code == 200
    alerts = client.get("/chatops/alerts").json()["alerts"]
    acked = next(a for a in alerts if a["id"] == alert_id)
    assert acked["acked"] == 1


def test_alerts_filter_unacked(client):
    from chatops.db import add_alert, ack_alert
    add_alert("Unacked", "WARNING")
    ack_alert(add_alert("Acked", "INFO"))
    alerts = client.get("/chatops/alerts?unacked_only=true").json()["alerts"]
    assert all(a["acked"] == 0 for a in alerts)


# ── Metrics history ───────────────────────────────────────────────────────────

def test_metrics_history_disk(client):
    resp = client.get("/chatops/metrics/history?metric=disk")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_metrics_history_memory(client):
    resp = client.get("/chatops/metrics/history?metric=memory")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_metrics_history_cpu(client):
    resp = client.get("/chatops/metrics/history?metric=cpu")
    assert resp.status_code == 200
    assert "data" in resp.json()


# ── Config ────────────────────────────────────────────────────────────────────

def test_config_get(client):
    resp = client.get("/chatops/config")
    assert resp.status_code == 200
    cfg = resp.json()
    for key in ["disk_warning", "disk_critical", "memory_warning",
                "memory_critical", "cpu_warning", "cpu_critical", "health_check_interval"]:
        assert key in cfg


def test_config_update(client):
    client.put("/chatops/config", json={"disk_warning": 75.0})
    assert client.get("/chatops/config").json()["disk_warning"] == 75.0


def test_config_partial_update(client):
    client.put("/chatops/config", json={"disk_warning": 75.0})
    cfg = client.get("/chatops/config").json()
    assert cfg["disk_critical"] == 90.0
    assert cfg["memory_warning"] == 80.0


# ── Runbooks ──────────────────────────────────────────────────────────────────

def test_runbooks_list(client):
    resp = client.get("/chatops/runbooks")
    assert resp.status_code == 200
    runbooks = resp.json()["runbooks"]
    assert len(runbooks) == 7
    for rb in runbooks:
        assert all(k in rb for k in ["name", "description", "preview"])


# ── Nodes ─────────────────────────────────────────────────────────────────────

def test_nodes_endpoint_returns_list(client):
    resp = client.get("/chatops/nodes")
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    assert isinstance(nodes, list)
    assert len(nodes) >= 1
    names = [n["name"] for n in nodes]
    assert "local" in names


def test_nodes_endpoint_has_fields(client):
    resp = client.get("/chatops/nodes")
    for node in resp.json()["nodes"]:
        assert all(k in node for k in ["name", "host", "user", "key_path"])


def test_node_config_get_local(client):
    resp = client.get("/chatops/nodes/local/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "thresholds" in data
    assert "is_default" in data
    for key in ["disk_warning", "disk_critical", "memory_warning",
                "memory_critical", "cpu_warning", "cpu_critical"]:
        assert key in data["thresholds"]


# ── Report endpoint ───────────────────────────────────────────────────────────

def test_report_endpoint(client):
    resp = client.get("/chatops/report")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "generated_at" in data
    assert "hours" in data


def test_report_endpoint_custom_hours(client):
    resp = client.get("/chatops/report?hours=12")
    assert resp.status_code == 200
    assert resp.json()["hours"] == 12


# ── Alerts node filter ────────────────────────────────────────────────────────

def test_alerts_filter_by_node(client):
    from chatops.db import add_alert
    add_alert("Local alert", "WARNING", node="local")
    add_alert("Remote alert", "WARNING", node="filternode")
    resp = client.get("/chatops/alerts?node=filternode")
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    assert all(a.get("node") == "filternode" for a in alerts)


# ── Metrics node filter ───────────────────────────────────────────────────────

def test_metrics_history_by_node(client):
    from chatops.db import add_metric
    add_metric("disk", 55.0, node="metricnode")
    resp = client.get("/chatops/metrics/history?metric=disk&node=metricnode")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert data[0]["value"] == 55.0


# ── Upload log ────────────────────────────────────────────────────────────────

def test_upload_log(client):
    log_content = b"ERROR: database connection refused\nERROR: timeout\n"
    resp = client.post(
        "/chatops/upload-log",
        files={"file": ("test.log", log_content, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "filename" in data
    assert data["filename"] == "test.log"
    assert "Severity" in data["response"]


# ── Analytics API ─────────────────────────────────────────────────────────────

def test_analytics_endpoint(client):
    resp = client.get("/chatops/analytics", headers={"Authorization": "Bearer " + _admin_token(client)})
    assert resp.status_code == 200
    data = resp.json()
    assert "alert_stats" in data
    assert "mttr" in data
    assert "top_commands" in data


def test_analytics_endpoint_unauthorized(client):
    resp = client.get("/chatops/analytics", headers={"Authorization": "Bearer bad_token"})
    assert resp.status_code == 401 or resp.status_code == 403


def test_analytics_pdf_endpoint(client):
    resp = client.get(
        "/chatops/analytics/report.pdf",
        headers={"Authorization": "Bearer " + _admin_token(client)},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 100


def test_analytics_pdf_unauthorized(client):
    resp = client.get("/chatops/analytics/report.pdf", headers={"Authorization": "Bearer bad_token"})
    assert resp.status_code in (401, 403)


def test_analytics_with_period(client):
    resp = client.get(
        "/chatops/analytics?days=30",
        headers={"Authorization": "Bearer " + _admin_token(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["alert_stats"]["days"] == 30


# ── Slack events endpoint ─────────────────────────────────────────────────────

def test_slack_url_verification(client):
    resp = client.post(
        "/chatops/slack/events",
        json={"type": "url_verification", "challenge": "test_challenge_abc"},
    )
    assert resp.status_code == 200
    assert resp.json()["challenge"] == "test_challenge_abc"


def _admin_token(client):
    resp = client.post("/chatops/auth/login", json={"username": "admin", "password": "admin"})
    return resp.json()["token"]


# ── Prometheus metrics endpoint ───────────────────────────────────────────────

def test_prometheus_endpoint_returns_200(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert resp.status_code == 200


def test_prometheus_content_type(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert "text/plain" in resp.headers["content-type"]


def test_prometheus_has_alert_metrics(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert "chatops_alerts_total" in resp.text


def test_prometheus_has_unacked_metric(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert "chatops_alerts_unacked" in resp.text


def test_prometheus_has_mttr_metric(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert "chatops_mttr_minutes_avg" in resp.text


def test_prometheus_has_system_usage(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert "chatops_system_usage_percent" in resp.text
    assert 'resource="disk"' in resp.text
    assert 'resource="memory"' in resp.text
    assert 'resource="cpu"' in resp.text


def test_prometheus_has_top_commands(client):
    resp = client.get("/chatops/metrics/prometheus")
    assert "chatops_top_commands_total" in resp.text


def test_prometheus_unauthorized(client):
    resp = client.get("/chatops/metrics/prometheus", headers={"Authorization": "Bearer bad_token"})
    assert resp.status_code in (401, 403)


def test_prometheus_valid_format(client):
    resp = client.get("/chatops/metrics/prometheus")
    for line in resp.text.splitlines():
        if line and not line.startswith("#"):
            # Each metric line must have a space separating name/labels from value
            assert " " in line


# ── Dry-run API (via message endpoint) ───────────────────────────────────────

def test_dry_run_via_message(client):
    resp = client.post("/chatops/message", json={"message": "dry run clear_tmp"})
    assert resp.status_code == 200
    assert "[DRY RUN]" in resp.json()["response"]


def test_dry_run_unknown_via_message(client):
    resp = client.post("/chatops/message", json={"message": "dry run xyz_nonexistent"})
    assert resp.status_code == 200
    assert "Unknown" in resp.json()["response"] or "Available" in resp.json()["response"]


# ── Predictive alerts API (via message endpoint) ──────────────────────────────

def test_predictive_alerts_via_message(client):
    resp = client.post("/chatops/message", json={"message": "show predictive alerts"})
    assert resp.status_code == 200
    assert resp.json()["response"]


# ── Feature 1: Auto-link alert → ticket (API) ─────────────────────────────────

def test_create_ticket_with_alert_link_via_message(client):
    from chatops.db import add_alert, ticket_list
    aid = add_alert("API alert link test", "WARNING")
    resp = client.post("/chatops/message", json={"message": f"create ticket API linked ticket priority high alert {aid}"})
    assert resp.status_code == 200
    body = resp.json()["response"]
    assert "Ticket #" in body
    assert f"#{aid}" in body or "linked" in body.lower()
    tickets = ticket_list(status="open")
    linked = next((t for t in tickets if t.get("alert_id") == aid), None)
    assert linked is not None
    assert linked["priority"] == "high"


def test_create_ticket_no_alert_link_omits_note(client):
    resp = client.post("/chatops/message", json={"message": "create ticket Plain ticket no link"})
    assert resp.status_code == 200
    assert "Linked" not in resp.json()["response"]


# ── Feature 3: PagerDuty webhook ingestion ────────────────────────────────────

def test_pagerduty_webhook_v2_message_envelope(client):
    payload = {
        "messages": [{
            "event": {
                "data": {
                    "title": "High CPU on web-01",
                    "severity": "critical"
                }
            }
        }]
    }
    resp = client.post("/chatops/webhooks/pagerduty", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] == 1
    assert len(data["alert_ids"]) == 1
    assert isinstance(data["alert_ids"][0], int)


def test_pagerduty_webhook_creates_critical_alert(client):
    from chatops.db import get_alerts
    payload = {"messages": [{"event": {"data": {"title": "PD CRITICAL test", "severity": "critical"}}}]}
    client.post("/chatops/webhooks/pagerduty", json=payload)
    alerts = get_alerts(limit=50)
    match = next((a for a in alerts if "PD CRITICAL test" in a["message"]), None)
    assert match is not None
    assert match["severity"] == "CRITICAL"
    assert match["source"] == "pagerduty"


def test_pagerduty_webhook_severity_mapping(client):
    from chatops.db import get_alerts
    for pd_sev, expected in [("warning", "WARNING"), ("info", "INFO"), ("error", "ERROR")]:
        payload = {"messages": [{"event": {"data": {"title": f"PD sev {pd_sev}", "severity": pd_sev}}}]}
        client.post("/chatops/webhooks/pagerduty", json=payload)
    alerts = get_alerts(limit=100)
    for label, expected_sev in [("PD sev warning", "WARNING"), ("PD sev info", "INFO"), ("PD sev error", "ERROR")]:
        match = next((a for a in alerts if label in a["message"]), None)
        assert match is not None, f"Missing alert for {label}"
        assert match["severity"] == expected_sev


def test_pagerduty_webhook_multi_message(client):
    payload = {
        "messages": [
            {"event": {"data": {"title": "PD multi 1", "severity": "warning"}}},
            {"event": {"data": {"title": "PD multi 2", "severity": "info"}}},
        ]
    }
    resp = client.post("/chatops/webhooks/pagerduty", json=payload)
    assert resp.status_code == 200
    assert resp.json()["received"] == 2
    assert len(resp.json()["alert_ids"]) == 2


def test_pagerduty_webhook_invalid_json(client):
    resp = client.post("/chatops/webhooks/pagerduty",
                       content=b"not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400


def test_pagerduty_webhook_empty_envelope(client):
    resp = client.post("/chatops/webhooks/pagerduty", json={})
    assert resp.status_code == 200
    assert resp.json()["received"] == 1


# ── Feature 3: Datadog webhook ingestion ─────────────────────────────────────

def test_datadog_webhook_creates_alert(client):
    from chatops.db import get_alerts
    payload = {"title": "Datadog: disk usage high", "alert_type": "error"}
    resp = client.post("/chatops/webhooks/datadog", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] == 1
    assert isinstance(data["alert_id"], int)
    alerts = get_alerts(limit=50)
    match = next((a for a in alerts if "Datadog: disk usage high" in a["message"]), None)
    assert match is not None
    assert match["source"] == "datadog"
    assert match["severity"] == "CRITICAL"


def test_datadog_webhook_severity_mapping(client):
    from chatops.db import get_alerts
    for dd_type, expected in [("warning", "WARNING"), ("info", "INFO"), ("success", "INFO")]:
        client.post("/chatops/webhooks/datadog", json={"title": f"DD {dd_type}", "alert_type": dd_type})
    alerts = get_alerts(limit=100)
    for label, expected_sev in [("DD warning", "WARNING"), ("DD info", "INFO"), ("DD success", "INFO")]:
        match = next((a for a in alerts if label in a["message"]), None)
        assert match is not None
        assert match["severity"] == expected_sev


def test_datadog_webhook_uses_event_title_fallback(client):
    from chatops.db import get_alerts
    payload = {"event_title": "DD event_title field", "alert_type": "warning"}
    client.post("/chatops/webhooks/datadog", json=payload)
    alerts = get_alerts(limit=50)
    assert any("DD event_title field" in a["message"] for a in alerts)


def test_datadog_webhook_invalid_json(client):
    resp = client.post("/chatops/webhooks/datadog",
                       content=b"not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400


# ── Feature 4: Custom Runbooks CRUD API ──────────────────────────────────────

def test_custom_runbooks_list_empty(client):
    from chatops.db import runbook_list, runbook_delete
    for rb in runbook_list():
        runbook_delete(rb["name"])
    resp = client.get("/chatops/custom-runbooks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_custom_runbooks_create(client):
    from chatops.db import runbook_delete
    payload = {"name": "api_test_rb", "description": "API test", "steps": '[{"label":"ls","command":"ls"}]'}
    resp = client.post("/chatops/custom-runbooks", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "api_test_rb"
    assert "id" in data
    runbook_delete("api_test_rb")


def test_custom_runbooks_create_invalid_steps(client):
    payload = {"name": "bad_steps_rb", "description": "Bad", "steps": "not json"}
    resp = client.post("/chatops/custom-runbooks", json=payload)
    assert resp.status_code == 400


def test_custom_runbooks_create_steps_not_array(client):
    payload = {"name": "obj_steps_rb", "description": "Bad", "steps": '{"key":"value"}'}
    resp = client.post("/chatops/custom-runbooks", json=payload)
    assert resp.status_code == 400


def test_custom_runbooks_create_duplicate(client):
    from chatops.db import runbook_delete
    payload = {"name": "dup_api_rb", "description": "First", "steps": "[]"}
    client.post("/chatops/custom-runbooks", json=payload)
    resp = client.post("/chatops/custom-runbooks", json=payload)
    assert resp.status_code == 409
    runbook_delete("dup_api_rb")


def test_custom_runbooks_list_shows_created(client):
    from chatops.db import runbook_delete
    client.post("/chatops/custom-runbooks",
                json={"name": "list_api_rb", "description": "List test", "steps": "[]"})
    resp = client.get("/chatops/custom-runbooks")
    assert resp.status_code == 200
    names = [rb["name"] for rb in resp.json()]
    assert "list_api_rb" in names
    runbook_delete("list_api_rb")


def test_custom_runbooks_delete(client):
    client.post("/chatops/custom-runbooks",
                json={"name": "del_api_rb", "description": "Delete me", "steps": "[]"})
    resp = client.delete("/chatops/custom-runbooks/del_api_rb")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == "del_api_rb"


def test_custom_runbooks_delete_nonexistent(client):
    resp = client.delete("/chatops/custom-runbooks/nonexistent_xyz_rb")
    assert resp.status_code == 404


def test_custom_runbooks_requires_auth():
    from fastapi.testclient import TestClient
    import app as app_module
    with TestClient(app_module.app) as c:
        resp = c.get("/chatops/custom-runbooks")
        assert resp.status_code == 401


def test_custom_runbooks_delete_requires_admin(client):
    from chatops.db import runbook_create, runbook_delete
    runbook_create("op_del_rb", "Operator delete test", "[]", created_by="admin")
    # Create an operator-level token
    import app as app_module
    from fastapi.testclient import TestClient
    with TestClient(app_module.app) as c:
        from chatops.db import create_user as _cu
        from chatops.auth import hash_password as _hp
        _cu("op_del_test", _hp("pass123"), "operator")
        login = c.post("/chatops/auth/login", json={"username": "op_del_test", "password": "pass123"})
        op_token = login.json()["token"]
        resp = c.delete("/chatops/custom-runbooks/op_del_rb",
                        headers={"Authorization": f"Bearer {op_token}"})
        assert resp.status_code == 403
    runbook_delete("op_del_rb")
