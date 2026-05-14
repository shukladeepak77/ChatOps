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
