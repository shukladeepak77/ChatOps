import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    async def _noop():
        pass
    import app as app_module
    monkeypatch.setattr(app_module, "_health_check_loop", _noop)
    from app import app
    with TestClient(app) as c:
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
    assert len(runbooks) == 4
    for rb in runbooks:
        assert all(k in rb for k in ["name", "description", "preview"])
