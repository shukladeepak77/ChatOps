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
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                role          TEXT    NOT NULL DEFAULT 'operator',
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                active        INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT    NOT NULL DEFAULT 'system',
                command   TEXT    NOT NULL,
                result    TEXT,
                node      TEXT    DEFAULT 'local',
                timestamp TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS kb_articles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                tags       TEXT    NOT NULL DEFAULT '',
                created_by TEXT    NOT NULL DEFAULT 'admin',
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT    NOT NULL DEFAULT '',
                status      TEXT    NOT NULL DEFAULT 'open',
                priority    TEXT    NOT NULL DEFAULT 'medium',
                created_by  TEXT    NOT NULL DEFAULT 'system',
                alert_id    INTEGER,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                closed_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS custom_runbooks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT    NOT NULL DEFAULT '',
                steps       TEXT    NOT NULL DEFAULT '[]',
                created_by  TEXT    NOT NULL DEFAULT 'system',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS network_devices (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL UNIQUE,
                host         TEXT    NOT NULL,
                port         INTEGER NOT NULL DEFAULT 22,
                netconf_port INTEGER NOT NULL DEFAULT 830,
                username     TEXT    NOT NULL,
                password_enc TEXT    NOT NULL DEFAULT '',
                device_type  TEXT    NOT NULL DEFAULT 'cisco_xe',
                description  TEXT    NOT NULL DEFAULT '',
                created_by   TEXT    NOT NULL DEFAULT 'system',
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS network_config_backups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT    NOT NULL,
                config_text TEXT    NOT NULL,
                lines       INTEGER NOT NULL DEFAULT 0,
                backed_up_at TEXT   NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS network_interface_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT    NOT NULL,
                interface   TEXT    NOT NULL,
                status      TEXT    NOT NULL,
                protocol    TEXT    NOT NULL DEFAULT 'unknown',
                in_rate     INTEGER DEFAULT 0,
                out_rate    INTEGER DEFAULT 0,
                errors_in   INTEGER DEFAULT 0,
                errors_out  INTEGER DEFAULT 0,
                timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        for table in ('metrics_history', 'alerts'):
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if 'node' not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN node TEXT NOT NULL DEFAULT 'local'")
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            from chatops.auth import hash_password as _hp
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", _hp("admin"), "admin"),
            )


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


def get_metric_stats(metric: str, since_hours: int = 24, node: str = None) -> dict:
    """Return avg, min, max for a metric over the past N hours, optionally filtered by node."""
    conn = _get_conn()
    if node:
        row = conn.execute(
            """
            SELECT
                ROUND(AVG(value), 1) as avg,
                ROUND(MIN(value), 1) as min_val,
                ROUND(MAX(value), 1) as max_val,
                COUNT(*)            as samples
            FROM metrics_history
            WHERE metric = ? AND node = ?
              AND timestamp >= datetime('now', ? || ' hours')
            """,
            (metric, node, f"-{since_hours}"),
        ).fetchone()
    else:
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


# ── Users ──────────────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, role: str = "operator") -> bool:
    try:
        with _conn() as conn:
            existing = conn.execute(
                "SELECT id, active FROM users WHERE username=?", (username,)
            ).fetchone()
            if existing:
                if not existing["active"]:
                    conn.execute(
                        "UPDATE users SET password_hash=?, role=?, active=1 WHERE username=?",
                        (password_hash, role, username),
                    )
                    return True
                return False
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def delete_user(username: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM users WHERE username=?", (username,))
    return cur.rowcount > 0


def get_user(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND active=1", (username,)
        ).fetchone()
    return dict(row) if row else None


def list_users() -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at, active FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def update_user_role(username: str, role: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE username=?", (role, username))
    return cur.rowcount > 0


def set_user_active(username: str, active: bool) -> bool:
    with _conn() as conn:
        cur = conn.execute("UPDATE users SET active=? WHERE username=?", (int(active), username))
    return cur.rowcount > 0


# ── Audit log ──────────────────────────────────────────────────────────────────

def add_audit(username: str, command: str, result: str = None, node: str = "local"):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (username, command, result, node) VALUES (?, ?, ?, ?)",
            (username, command, result, node),
        )


def get_audit_log(limit: int = 50, username: str = None, node: str = None) -> List[Dict]:
    with _conn() as conn:
        conditions, params = [], []
        if username:
            conditions.append("username=?")
            params.append(username)
        if node:
            conditions.append("node=?")
            params.append(node)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM audit_log{where} ORDER BY id DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    return [dict(r) for r in rows]


def get_alert_count(since_hours: int = 24, node: str = None) -> dict:
    """Return total and unacked alert counts over the past N hours, optionally filtered by node."""
    conn = _get_conn()
    if node:
        row = conn.execute(
            """
            SELECT
                COUNT(*)                              as total,
                SUM(CASE WHEN acked=0 THEN 1 ELSE 0 END) as unacked
            FROM alerts
            WHERE node = ?
              AND timestamp >= datetime('now', ? || ' hours')
            """,
            (node, f"-{since_hours}"),
        ).fetchone()
    else:
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


# ── Knowledge Base ─────────────────────────────────────────────────────────────

def kb_add(title: str, content: str, tags: str = "", created_by: str = "admin") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO kb_articles (title, content, tags, created_by) VALUES (?, ?, ?, ?)",
            (title.strip(), content.strip(), tags.strip(), created_by),
        )
    return cur.lastrowid


def kb_search(query: str) -> List[Dict]:
    q = f"%{query}%"
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, tags, created_by, created_at FROM kb_articles "
            "WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY id DESC",
            (q, q, q),
        ).fetchall()
    return [dict(r) for r in rows]


def kb_get(article_id: int) -> Dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM kb_articles WHERE id=?", (article_id,)).fetchone()
    return dict(row) if row else None


def kb_list(limit: int = 20) -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, tags, created_by, created_at FROM kb_articles ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def kb_delete(article_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM kb_articles WHERE id=?", (article_id,))
    return cur.rowcount > 0


# ── Tickets (ITSM) ────────────────────────────────────────────────────────────

def ticket_create(title: str, description: str = "", priority: str = "medium",
                  created_by: str = "system", alert_id: int = None) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (title, description, priority, created_by, alert_id) VALUES (?,?,?,?,?)",
            (title, description, priority, created_by, alert_id),
        )
    return cur.lastrowid


def ticket_list(status: str = "open", limit: int = 20) -> List[Dict]:
    with _conn() as conn:
        if status == "all":
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tickets WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)
            ).fetchall()
    return [dict(r) for r in rows]


def ticket_get(ticket_id: int) -> Dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def ticket_close(ticket_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE tickets SET status='closed', closed_at=datetime('now'), updated_at=datetime('now') WHERE id=? AND status='open'",
            (ticket_id,),
        )
    return cur.rowcount > 0


def ticket_update(ticket_id: int, **fields) -> bool:
    allowed = {"title", "description", "priority", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = "datetime('now')"
    set_clause = ", ".join(f"{k}=?" for k in updates if k != "updated_at")
    set_clause += ", updated_at=datetime('now')"
    vals = [v for k, v in updates.items() if k != "updated_at"]
    with _conn() as conn:
        cur = conn.execute(f"UPDATE tickets SET {set_clause} WHERE id=?", vals + [ticket_id])
    return cur.rowcount > 0


# ── Custom Runbooks ───────────────────────────────────────────────────────────

def runbook_create(name: str, description: str, steps: str, created_by: str = "system") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO custom_runbooks (name, description, steps, created_by) VALUES (?,?,?,?)",
            (name, description, steps, created_by),
        )
    return cur.lastrowid


def runbook_list() -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM custom_runbooks ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def runbook_get(name: str) -> Dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM custom_runbooks WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def runbook_delete(name: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM custom_runbooks WHERE name=?", (name,))
    return cur.rowcount > 0


# ── Network Devices ───────────────────────────────────────────────────────────

def netdev_add(name: str, host: str, username: str, password_enc: str,
               device_type: str = "cisco_xe", port: int = 22,
               netconf_port: int = 830, description: str = "",
               created_by: str = "system") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO network_devices "
            "(name, host, port, netconf_port, username, password_enc, device_type, description, created_by) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (name, host, port, netconf_port, username, password_enc,
             device_type, description, created_by),
        )
    return cur.lastrowid


def netdev_get(name: str) -> Dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM network_devices WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def netdev_list() -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, name, host, port, netconf_port, username, device_type, description, created_at "
            "FROM network_devices ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def netdev_delete(name: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM network_devices WHERE name=?", (name,))
    return cur.rowcount > 0


# ── Config Backups ────────────────────────────────────────────────────────────

def netdev_save_backup(device_name: str, config_text: str, lines: int) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO network_config_backups (device_name, config_text, lines) VALUES (?,?,?)",
            (device_name, config_text, lines),
        )
    return cur.lastrowid


def netdev_get_backup(device_name: str) -> Dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM network_config_backups WHERE device_name=? ORDER BY id DESC LIMIT 1",
            (device_name,),
        ).fetchone()
    return dict(row) if row else None


def netdev_list_backups(device_name: str, limit: int = 10) -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, device_name, lines, backed_up_at FROM network_config_backups "
            "WHERE device_name=? ORDER BY id DESC LIMIT ?",
            (device_name, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Interface Log ─────────────────────────────────────────────────────────────

def netdev_log_interfaces(device_name: str, interfaces: list):
    with _conn() as conn:
        for iface in interfaces:
            conn.execute(
                "INSERT INTO network_interface_log "
                "(device_name, interface, status, protocol, in_rate, out_rate, errors_in, errors_out) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (device_name, iface.get("interface", ""),
                 iface.get("status", "unknown"), iface.get("protocol", "unknown"),
                 iface.get("in_rate") or 0, iface.get("out_rate") or 0,
                 iface.get("errors_in") or 0, iface.get("errors_out") or 0),
            )


def netdev_get_interface_history(device_name: str, interface: str, limit: int = 60) -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM network_interface_log WHERE device_name=? AND interface=? "
            "ORDER BY id DESC LIMIT ?",
            (device_name, interface, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]
