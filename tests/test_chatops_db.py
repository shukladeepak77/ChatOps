from chatops.db import (
    get_history, save_message, clear_history,
    add_alert, get_alerts, ack_alert, unacked_count,
    add_metric, get_metric_history,
    get_metric_stats, get_alert_count,
    get_last_notified, set_last_notified,
    ticket_create, ticket_get, ticket_list, ticket_close, ticket_update,
    runbook_create, runbook_list, runbook_get, runbook_delete,
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


# ── Node-tagged metrics ───────────────────────────────────────────────────────

def test_add_metric_with_node():
    add_metric("disk", 60.0, node="nodeA")
    add_metric("disk", 80.0, node="nodeB")
    nodeA_data = get_metric_history("disk", node="nodeA")
    assert len(nodeA_data) == 1
    assert nodeA_data[0]["value"] == 60.0


def test_get_metric_history_filters_by_node():
    add_metric("cpu", 50.0, node="nodeA")
    add_metric("cpu", 70.0, node="nodeB")
    nodeB_data = get_metric_history("cpu", node="nodeB")
    assert all(r["value"] == 70.0 for r in nodeB_data)


def test_get_metric_stats_by_node():
    add_metric("memory", 40.0, node="statsnode")
    add_metric("memory", 60.0, node="statsnode")
    stats = get_metric_stats("memory", since_hours=1, node="statsnode")
    assert stats["samples"] == 2
    assert stats["avg"] == 50.0
    assert stats["min"] == 40.0
    assert stats["max"] == 60.0


def test_get_metric_stats_no_data():
    stats = get_metric_stats("disk", since_hours=1, node="emptynode")
    assert stats["samples"] == 0
    assert stats["avg"] is None


# ── Node-tagged alerts ────────────────────────────────────────────────────────

def test_add_alert_with_node():
    add_alert("Disk CRITICAL on nodeX", "CRITICAL", node="nodeX")
    alerts = get_alerts(node="nodeX")
    assert len(alerts) == 1
    assert alerts[0]["message"] == "Disk CRITICAL on nodeX"


def test_get_alerts_filters_by_node():
    add_alert("Alert nodeA", "WARNING", node="nodeA")
    add_alert("Alert nodeB", "WARNING", node="nodeB")
    nodeA_alerts = get_alerts(node="nodeA")
    assert all("nodeA" in a["message"] for a in nodeA_alerts)


def test_unacked_count_by_node():
    add_alert("A on nodeC", "CRITICAL", node="nodeC")
    add_alert("B on nodeC", "WARNING", node="nodeC")
    add_alert("C on nodeD", "WARNING", node="nodeD")
    assert unacked_count(node="nodeC") == 2
    assert unacked_count(node="nodeD") == 1


def test_get_alert_count_by_node():
    add_alert("X on nodeE", "CRITICAL", node="nodeE")
    add_alert("Y on nodeE", "WARNING", node="nodeE")
    counts = get_alert_count(since_hours=1, node="nodeE")
    assert counts["total"] == 2
    assert counts["unacked"] == 2


# ── Alert suppression ─────────────────────────────────────────────────────────

def test_last_notified_initially_none():
    assert get_last_notified("disk_unique_xyz") is None


def test_set_and_get_last_notified():
    set_last_notified("memory_test_key")
    result = get_last_notified("memory_test_key")
    assert result is not None


def test_set_last_notified_upserts():
    set_last_notified("cpu_test_key")
    first = get_last_notified("cpu_test_key")
    set_last_notified("cpu_test_key")
    second = get_last_notified("cpu_test_key")
    assert second >= first


# ── Tickets ───────────────────────────────────────────────────────────────────

def test_ticket_create_returns_id():
    tid = ticket_create("Test ticket", priority="medium", created_by="admin")
    assert isinstance(tid, int) and tid > 0


def test_ticket_get_fields():
    tid = ticket_create("Field check ticket", description="desc", priority="high", created_by="admin")
    t = ticket_get(tid)
    assert t is not None
    for field in ["id", "title", "description", "status", "priority", "created_by", "created_at"]:
        assert field in t


def test_ticket_default_status_open():
    tid = ticket_create("Status check", created_by="admin")
    assert ticket_get(tid)["status"] == "open"


def test_ticket_create_with_alert_link():
    aid = add_alert("Linked alert", "WARNING")
    tid = ticket_create("Linked ticket", priority="high", created_by="admin", alert_id=aid)
    t = ticket_get(tid)
    assert t["alert_id"] == aid


def test_ticket_list_open_only():
    tid = ticket_create("Open ticket", created_by="admin")
    ticket_close(tid)
    open_tickets = ticket_list(status="open")
    assert all(t["status"] == "open" for t in open_tickets)


def test_ticket_list_all():
    ticket_create("For all list", created_by="admin")
    all_tickets = ticket_list(status="all")
    statuses = {t["status"] for t in all_tickets}
    assert "open" in statuses


def test_ticket_close():
    tid = ticket_create("To close", created_by="admin")
    assert ticket_close(tid) is True
    t = ticket_get(tid)
    assert t["status"] == "closed"
    assert t["closed_at"] is not None


def test_ticket_close_already_closed():
    tid = ticket_create("Already closed", created_by="admin")
    ticket_close(tid)
    assert ticket_close(tid) is False


def test_ticket_close_nonexistent():
    assert ticket_close(999999) is False


def test_ticket_update_priority():
    tid = ticket_create("Update me", priority="low", created_by="admin")
    assert ticket_update(tid, priority="high") is True
    assert ticket_get(tid)["priority"] == "high"


def test_ticket_update_title():
    tid = ticket_create("Old title", created_by="admin")
    assert ticket_update(tid, title="New title") is True
    assert ticket_get(tid)["title"] == "New title"


def test_ticket_update_no_fields():
    tid = ticket_create("No update", created_by="admin")
    assert ticket_update(tid) is False


# ── Custom Runbooks ───────────────────────────────────────────────────────────

def test_runbook_create_returns_id():
    rid = runbook_create("test_rb_db", "Test runbook", '[{"label":"ls","command":"ls"}]', created_by="admin")
    assert isinstance(rid, int) and rid > 0
    runbook_delete("test_rb_db")


def test_runbook_get_fields():
    runbook_create("rb_fields", "Fields test", '[]', created_by="admin")
    rb = runbook_get("rb_fields")
    assert rb is not None
    for field in ["id", "name", "description", "steps", "created_by", "created_at"]:
        assert field in rb
    runbook_delete("rb_fields")


def test_runbook_get_nonexistent():
    assert runbook_get("nonexistent_xyz_rb") is None


def test_runbook_list_includes_created():
    runbook_create("rb_list_test", "List test", '[]', created_by="admin")
    names = [rb["name"] for rb in runbook_list()]
    assert "rb_list_test" in names
    runbook_delete("rb_list_test")


def test_runbook_delete_returns_true():
    runbook_create("rb_to_delete", "Delete me", '[]', created_by="admin")
    assert runbook_delete("rb_to_delete") is True


def test_runbook_delete_nonexistent():
    assert runbook_delete("nonexistent_xyz_rb") is False


def test_runbook_name_unique():
    import pytest
    runbook_create("rb_unique", "First", '[]', created_by="admin")
    with pytest.raises(Exception):
        runbook_create("rb_unique", "Duplicate", '[]', created_by="admin")
    runbook_delete("rb_unique")
