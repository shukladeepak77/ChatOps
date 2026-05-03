from chatops.db import (
    get_history, save_message, clear_history,
    add_alert, get_alerts, ack_alert, unacked_count,
    add_metric, get_metric_history,
)


# ── Chat history ──────────────────────────────────────────────────────────────

def test_init_db_creates_tables():
    assert get_history() == []


def test_save_and_get_history():
    save_message("user", "hello")
    save_message("bot", "world")
    history = get_history()
    assert len(history) == 2
    assert history[0]["message"] == "hello"
    assert history[1]["message"] == "world"


def test_history_order():
    save_message("user", "first")
    save_message("bot", "second")
    save_message("user", "third")
    history = get_history()
    assert history[0]["message"] == "first"
    assert history[2]["message"] == "third"


def test_history_limit():
    for i in range(10):
        save_message("user", f"msg{i}")
    assert len(get_history(limit=3)) == 3


def test_clear_history():
    save_message("user", "to be cleared")
    clear_history()
    assert get_history() == []


# ── Alerts ────────────────────────────────────────────────────────────────────

def test_add_and_get_alerts():
    add_alert("Disk WARNING: 85% used", "WARNING")
    alerts = get_alerts()
    assert len(alerts) == 1
    assert alerts[0]["message"] == "Disk WARNING: 85% used"


def test_alert_fields():
    add_alert("Test", "INFO")
    alert = get_alerts()[0]
    for field in ["id", "message", "severity", "timestamp", "acked"]:
        assert field in alert


def test_ack_alert():
    add_alert("To ack", "WARNING")
    alert_id = get_alerts()[0]["id"]
    ack_alert(alert_id)
    alert = get_alerts()[0]
    assert alert["acked"] == 1
    assert alert["acked_at"] is not None


def test_unacked_count():
    add_alert("A", "WARNING")
    add_alert("B", "CRITICAL")
    assert unacked_count() == 2
    ack_alert(get_alerts()[-1]["id"])
    assert unacked_count() == 1


def test_get_alerts_unacked_only():
    add_alert("X", "WARNING")
    add_alert("Y", "INFO")
    ack_alert(get_alerts()[-1]["id"])
    unacked = get_alerts(unacked_only=True)
    assert len(unacked) == 1
    assert all(a["acked"] == 0 for a in unacked)


# ── Metrics history ───────────────────────────────────────────────────────────

def test_add_and_get_metrics():
    add_metric("disk", 55.0)
    data = get_metric_history("disk")
    assert len(data) == 1
    assert data[0]["value"] == 55.0


def test_metrics_filter_by_name():
    add_metric("disk", 55.0)
    add_metric("cpu", 30.0)
    add_metric("memory", 40.0)
    cpu_data = get_metric_history("cpu")
    assert len(cpu_data) == 1
    assert cpu_data[0]["value"] == 30.0


def test_metrics_limit():
    for i in range(10):
        add_metric("disk", float(i))
    assert len(get_metric_history("disk", limit=3)) == 3


def test_metrics_chronological_order():
    add_metric("memory", 10.0)
    add_metric("memory", 20.0)
    add_metric("memory", 30.0)
    data = get_metric_history("memory")
    assert data[0]["value"] == 10.0
    assert data[-1]["value"] == 30.0
