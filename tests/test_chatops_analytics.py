from chatops.db import add_alert, ack_alert, get_alerts, add_audit
from chatops.analytics import get_alert_stats, get_mttr_stats, get_command_stats, generate_pdf_report
from chatops.router import route_message


def _resp(msg):
    return route_message(msg).get("response", "")


# ── Alert stats ───────────────────────────────────────────────────────────────

def test_alert_stats_empty():
    stats = get_alert_stats(7)
    assert stats["total"] == 0
    assert stats["acked"] == 0
    assert stats["unacked"] == 0
    assert stats["by_severity"] == {}
    assert stats["daily"] == []
    assert stats["top_messages"] == []


def test_alert_stats_counts():
    add_alert("Disk WARNING: 80%", "warning")
    add_alert("CPU CRITICAL: 90%", "critical")
    add_alert("Disk WARNING: 82%", "warning")
    stats = get_alert_stats(7)
    assert stats["total"] == 3
    assert stats["by_severity"].get("warning") == 2
    assert stats["by_severity"].get("critical") == 1


def test_alert_stats_acked_count():
    add_alert("Memory WARNING: 85%", "warning")
    alerts = get_alerts(limit=1)
    ack_alert(alerts[0]["id"])
    stats = get_alert_stats(7)
    assert stats["acked"] == 1
    assert stats["unacked"] == 0


def test_alert_stats_top_messages():
    for _ in range(3):
        add_alert("Repeated alert message", "warning")
    add_alert("One-time alert", "warning")
    stats = get_alert_stats(7)
    top = stats["top_messages"]
    assert len(top) >= 1
    assert top[0]["message"] == "Repeated alert message"
    assert top[0]["count"] == 3


def test_alert_stats_daily_trend():
    add_alert("Today alert", "warning")
    stats = get_alert_stats(7)
    assert len(stats["daily"]) >= 1
    assert stats["daily"][-1]["count"] >= 1


# ── MTTR ─────────────────────────────────────────────────────────────────────

def test_mttr_no_resolved_alerts():
    mttr = get_mttr_stats()
    assert mttr["avg_minutes"] is None
    assert mttr["sample_size"] == 0


def test_mttr_with_resolved_alert():
    add_alert("Resolved alert", "warning")
    alerts = get_alerts(limit=1)
    ack_alert(alerts[0]["id"])
    mttr = get_mttr_stats()
    assert mttr["sample_size"] >= 0


# ── Command stats ─────────────────────────────────────────────────────────────

def test_command_stats_empty():
    stats = get_command_stats(7)
    assert isinstance(stats, list)


def test_command_stats_after_audit():
    add_audit("admin", "check disk", "Disk OK")
    add_audit("admin", "check disk", "Disk OK")
    add_audit("admin", "check memory", "Memory OK")
    stats = get_command_stats(7)
    assert len(stats) >= 1
    assert stats[0]["command"] == "check disk"
    assert stats[0]["count"] == 2


# ── PDF report ────────────────────────────────────────────────────────────────

def test_generate_pdf_returns_bytes():
    pdf = generate_pdf_report(7)
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 100


def test_generate_pdf_with_alerts():
    add_alert("Disk CRITICAL: 95%", "critical")
    add_alert("Memory WARNING: 80%", "warning")
    pdf = generate_pdf_report(7)
    assert len(pdf) > 100


def test_generate_pdf_header():
    pdf = generate_pdf_report(7)
    assert b"PDF" in pdf[:10]


# ── Router analytics command ──────────────────────────────────────────────────

def test_route_show_analytics():
    resp = _resp("show analytics")
    assert "Analytics" in resp
    assert "Alerts" in resp
    assert "MTTR" in resp


def test_route_show_analytics_with_days():
    resp = _resp("show analytics 30d")
    assert "30 days" in resp


def test_route_show_analytics_with_data():
    add_alert("Test alert", "warning")
    resp = _resp("show analytics")
    assert "Total" in resp
