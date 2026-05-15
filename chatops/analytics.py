from datetime import datetime, timedelta, timezone
from .db import _conn


def get_alert_stats(days: int = 7) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE timestamp >= ?", (since,)
        ).fetchone()[0]
        by_severity = {
            r["severity"]: r["cnt"]
            for r in conn.execute(
                "SELECT severity, COUNT(*) cnt FROM alerts WHERE timestamp >= ? GROUP BY severity",
                (since,),
            ).fetchall()
        }
        daily = conn.execute(
            "SELECT DATE(timestamp) day, COUNT(*) cnt FROM alerts "
            "WHERE timestamp >= ? GROUP BY day ORDER BY day",
            (since,),
        ).fetchall()
        top_messages = conn.execute(
            "SELECT message, COUNT(*) cnt FROM alerts WHERE timestamp >= ? "
            "GROUP BY message ORDER BY cnt DESC LIMIT 5",
            (since,),
        ).fetchall()
        acked = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE timestamp >= ? AND acked=1", (since,)
        ).fetchone()[0]
    return {
        "days": days,
        "total": total,
        "acked": acked,
        "unacked": total - acked,
        "by_severity": by_severity,
        "daily": [{"day": r["day"], "count": r["cnt"]} for r in daily],
        "top_messages": [{"message": r["message"], "count": r["cnt"]} for r in top_messages],
    }


def get_mttr_stats(days: int = 7) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        # Filter on acked_at so we measure alerts *resolved* in the period
        rows = conn.execute(
            "SELECT timestamp, acked_at FROM alerts "
            "WHERE acked=1 AND acked_at IS NOT NULL AND acked_at != '' "
            "AND acked_at >= ?",
            (since,),
        ).fetchall()
    if not rows:
        return {"avg_minutes": None, "sample_size": 0}
    durations = []
    for r in rows:
        try:
            created = datetime.strptime(r["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
            resolved = datetime.strptime(r["acked_at"][:19], "%Y-%m-%d %H:%M:%S")
            diff = (resolved - created).total_seconds() / 60
            if diff > 0:
                durations.append(diff)
        except Exception:
            pass
    if not durations:
        return {"avg_minutes": None, "sample_size": 0}
    return {
        "avg_minutes": round(sum(durations) / len(durations), 1),
        "min_minutes": round(min(durations), 1),
        "max_minutes": round(max(durations), 1),
        "sample_size": len(durations),
    }


def get_mttr_trend(days: int = 7) -> list:
    """Per-day average MTTR for charting."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DATE(acked_at) day, timestamp, acked_at FROM alerts "
            "WHERE acked=1 AND acked_at IS NOT NULL AND acked_at != '' "
            "AND acked_at >= ? ORDER BY acked_at",
            (since,),
        ).fetchall()
    daily: dict = {}
    for r in rows:
        try:
            day = r["day"]
            created = datetime.strptime(r["timestamp"][:19], "%Y-%m-%d %H:%M:%S")
            resolved = datetime.strptime(r["acked_at"][:19], "%Y-%m-%d %H:%M:%S")
            diff = (resolved - created).total_seconds() / 60
            if diff > 0:
                daily.setdefault(day, []).append(diff)
        except Exception:
            pass
    return [{"day": day, "avg_minutes": round(sum(v) / len(v), 1)} for day, v in sorted(daily.items())]


def get_user_leaderboard(days: int = 7) -> list:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        rows = conn.execute(
            "SELECT username, COUNT(*) cnt FROM audit_log WHERE timestamp >= ? "
            "GROUP BY username ORDER BY cnt DESC LIMIT 10",
            (since,),
        ).fetchall()
    return [{"username": r["username"], "count": r["cnt"]} for r in rows]


def get_command_stats(days: int = 7) -> list:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        rows = conn.execute(
            "SELECT command, COUNT(*) cnt FROM audit_log WHERE timestamp >= ? "
            "GROUP BY command ORDER BY cnt DESC LIMIT 10",
            (since,),
        ).fetchall()
    return [{"command": r["command"], "count": r["cnt"]} for r in rows]


def generate_pdf_report(days: int = 7) -> bytes:
    from fpdf import FPDF, XPos, YPos

    alerts = get_alert_stats(days)
    mttr = get_mttr_stats(days)
    cmds = get_command_stats(days)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_fill_color(30, 58, 138)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_xy(10, 7)
    pdf.cell(0, 10, "ChatOps Analytics Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, 18)
    pdf.cell(0, 6, f"Generated: {now}  |  Period: last {days} days")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(18)

    def section(title):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 8, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

    def row(label, value, color=None):
        pdf.set_font("Helvetica", "", 10)
        if color:
            pdf.set_text_color(*color)
        pdf.cell(70, 7, f"  {label}", border="B")
        pdf.cell(0, 7, str(value), border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    # Alert Summary
    section("Alert Summary")
    row("Total Alerts", alerts["total"])
    row("Acknowledged", alerts["acked"])
    row("Unacknowledged", alerts["unacked"],
        color=(200, 50, 50) if alerts["unacked"] > 0 else None)
    for sev, cnt in sorted(alerts["by_severity"].items()):
        color = (200, 50, 50) if sev == "critical" else (220, 119, 6) if sev == "warning" else None
        row(f"  {sev.capitalize()}", cnt, color=color)
    pdf.ln(4)

    # MTTR
    section("Mean Time to Resolution (MTTR)")
    if mttr["avg_minutes"] is not None:
        row("Avg MTTR", f"{mttr['avg_minutes']} min")
        row("Min MTTR", f"{mttr['min_minutes']} min")
        row("Max MTTR", f"{mttr['max_minutes']} min")
        row("Sample Size", mttr["sample_size"])
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, "  No resolved alerts in this period.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Daily Alert Trend
    section("Daily Alert Trend")
    if alerts["daily"]:
        max_cnt = max(d["count"] for d in alerts["daily"]) or 1
        for d in alerts["daily"]:
            bar_w = int((d["count"] / max_cnt) * 80)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(28, 6, f"  {d['day']}")
            pdf.set_fill_color(99, 102, 241)
            pdf.cell(bar_w or 1, 5, "", fill=True)
            pdf.cell(5, 6, "")
            pdf.cell(0, 6, str(d["count"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, "  No alerts in this period.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Top Alert Messages
    section("Top Alert Messages")
    for m in alerts["top_messages"]:
        pdf.set_font("Helvetica", "", 10)
        msg = m["message"][:70] + "..." if len(m["message"]) > 70 else m["message"]
        pdf.cell(140, 7, f"  {msg}", border="B")
        pdf.cell(0, 7, str(m["count"]), border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Top Commands
    section(f"Top Commands (last {days} days)")
    for c in cmds[:8]:
        pdf.set_font("Helvetica", "", 10)
        cmd = c["command"][:60] + "..." if len(c["command"]) > 60 else c["command"]
        pdf.cell(140, 7, f"  {cmd}", border="B")
        pdf.cell(0, 7, str(c["count"]), border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, f"ChatOps Platform  |  {now}  |  Confidential", align="C")

    return pdf.output()
