import sqlite3
from typing import List, Dict

DB_PATH = "chatops.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                role      TEXT NOT NULL,
                message   TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                message   TEXT NOT NULL,
                severity  TEXT NOT NULL DEFAULT 'INFO',
                source    TEXT DEFAULT 'system',
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                acked     INTEGER NOT NULL DEFAULT 0,
                acked_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS metrics_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                metric    TEXT NOT NULL,
                value     REAL NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS alert_suppress (
                metric      TEXT PRIMARY KEY,
                notified_at TEXT NOT NULL
            );
        """)
        for table in ('metrics_history', 'alerts'):
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if 'node' not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN node TEXT NOT NULL DEFAULT 'local'")


# ── Chat history ──────────────────────────────────────────────────────────────

def save_message(role: str, message: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (role, message) VALUES (?, ?)",
            (role, message),
        )


def get_history(limit: int = 50) -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, role, message, timestamp FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def clear_history():
    with _conn() as conn:
        conn.execute("DELETE FROM chat_history")


# ── Alerts ────────────────────────────────────────────────────────────────────

def add_alert(message: str, severity: str = "INFO", source: str = "system", node: str = "local") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO alerts (message, severity, source, node) VALUES (?, ?, ?, ?)",
            (message, severity, source, node),
        )
        return cur.lastrowid


def get_alerts(limit: int = 50, unacked_only: bool = False, node: str = None) -> List[Dict]:
    with _conn() as conn:
        conditions, params = [], []
        if unacked_only:
            conditions.append("acked=0")
        if node:
            conditions.append("node=?")
            params.append(node)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM alerts{where} ORDER BY id DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    return [dict(r) for r in rows]


def ack_alert(alert_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE alerts SET acked=1, acked_at=datetime('now') WHERE id=?",
            (alert_id,),
        )


def unacked_count(node: str = None) -> int:
    with _conn() as conn:
        if node:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM alerts WHERE acked=0 AND node=?", (node,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM alerts WHERE acked=0").fetchone()
    return row["cnt"] if row else 0


# ── Metrics history ───────────────────────────────────────────────────────────

def add_metric(metric: str, value: float, node: str = 'local'):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO metrics_history (metric, value, node) VALUES (?, ?, ?)",
            (metric, value, node),
        )


def get_metric_history(metric: str, limit: int = 60, node: str = 'local') -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT value, timestamp FROM metrics_history WHERE metric=? AND node=? ORDER BY id DESC LIMIT ?",
            (metric, node, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def list_metric_nodes() -> List[str]:
    with _conn() as conn:
        rows = conn.execute("SELECT DISTINCT node FROM metrics_history ORDER BY node").fetchall()
    return [r["node"] for r in rows]


# ── Alert suppression ─────────────────────────────────────────────────────────

def _get_conn():
    return _conn()


def get_last_notified(metric: str) -> str | None:
    """Return ISO timestamp of last Slack notification for this metric, or None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT notified_at FROM alert_suppress WHERE metric = ?", (metric,)
    ).fetchone()
    return row["notified_at"] if row else None


def set_last_notified(metric: str):
    """Upsert the last notification timestamp for a metric."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO alert_suppress (metric, notified_at) VALUES (?, datetime('now')) "
        "ON CONFLICT(metric) DO UPDATE SET notified_at = datetime('now')",
        (metric,),
    )
    conn.commit()


def get_metric_stats(metric: str, since_hours: int = 24) -> dict:
    """Return avg, min, max for a metric over the past N hours."""
    conn = _get_conn()
    row = conn.execute(
        """
        SELECT
            ROUND(AVG(value), 1) as avg,
            ROUND(MIN(value), 1) as min_val,
            ROUND(MAX(value), 1) as max_val,
            COUNT(*)            as samples
        FROM metrics_history
        WHERE metric = ?
          AND timestamp >= datetime('now', ? || ' hours')
        """,
        (metric, f"-{since_hours}"),
    ).fetchone()
    if row and row["samples"]:
        return {
            "avg": row["avg"],
            "min": row["min_val"],
            "max": row["max_val"],
            "samples": row["samples"],
        }
    return {"avg": None, "min": None, "max": None, "samples": 0}


def get_alert_count(since_hours: int = 24) -> dict:
    """Return total and unacked alert counts over the past N hours."""
    conn = _get_conn()
    row = conn.execute(
        """
        SELECT
            COUNT(*)                              as total,
            SUM(CASE WHEN acked=0 THEN 1 ELSE 0 END) as unacked
        FROM alerts
        WHERE timestamp >= datetime('now', ? || ' hours')
        """,
        (f"-{since_hours}",),
    ).fetchone()
    return {
        "total":  row["total"]  or 0,
        "unacked": row["unacked"] or 0,
    }
