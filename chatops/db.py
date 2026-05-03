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
        """)


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

def add_alert(message: str, severity: str = "INFO", source: str = "system") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO alerts (message, severity, source) VALUES (?, ?, ?)",
            (message, severity, source),
        )
        return cur.lastrowid


def get_alerts(limit: int = 50, unacked_only: bool = False) -> List[Dict]:
    with _conn() as conn:
        if unacked_only:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE acked=0 ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def ack_alert(alert_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE alerts SET acked=1, acked_at=datetime('now') WHERE id=?",
            (alert_id,),
        )


def unacked_count() -> int:
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM alerts WHERE acked=0").fetchone()
    return row["cnt"] if row else 0


# ── Metrics history ───────────────────────────────────────────────────────────

def add_metric(metric: str, value: float):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO metrics_history (metric, value) VALUES (?, ?)",
            (metric, value),
        )


def get_metric_history(metric: str, limit: int = 60) -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT value, timestamp FROM metrics_history WHERE metric=? ORDER BY id DESC LIMIT ?",
            (metric, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]
