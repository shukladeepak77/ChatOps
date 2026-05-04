import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import pathlib

from chatops.router import route_message
from chatops.auth import decode_token, create_token, verify_password, hash_password, ROLE_LEVEL
from chatops.db import (
    init_db, save_message, get_history, clear_history,
    get_alerts, ack_alert, unacked_count, get_metric_history, add_alert,
    list_metric_nodes,
    get_user, create_user as db_create_user, list_users as db_list_users,
    update_user_role, set_user_active,
    add_audit, get_audit_log,
)
from chatops.config import load_config, save_config
from chatops.runbooks import list_runbooks


# ── Background health check ───────────────────────────────────────────────────

def _health_check_sync():
    from chatops.actions import check_disk, check_memory, check_cpu, notify_slack
    from chatops.config import alert_status_from_config, load_config
    from chatops.db import add_metric, add_alert, get_last_notified, set_last_notified
    from datetime import datetime, timezone
    import socket

    cfg = load_config()
    webhook = cfg.get("slack_webhook", "").strip()
    suppress_minutes = int(cfg.get("alert_suppress_minutes", 10))
    hostname = socket.gethostname()

    for fn, metric in [(check_disk, "disk"), (check_memory, "memory"), (check_cpu, "cpu")]:
        try:
            data = fn()
            pct = data["percent_used"]
            add_metric(metric, pct, node='local')
            status = alert_status_from_config(pct, metric)
            if status != "OK":
                add_alert(f"{metric.capitalize()} {status}: {pct:.1f}% used", status, node='local')

            if status == "CRITICAL" and webhook:
                last = get_last_notified(metric)
                should_notify = True
                if last:
                    from datetime import timedelta
                    last_dt = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
                    now_dt = datetime.now(timezone.utc)
                    if (now_dt - last_dt).total_seconds() < suppress_minutes * 60:
                        should_notify = False
                if should_notify:
                    ok, _ = notify_slack(webhook, metric, status, pct, hostname)
                    if ok:
                        set_last_notified(metric)
        except Exception:
            pass


def _poll_remote_nodes_sync():
    from chatops.nodes import list_nodes
    from chatops.ssh import get_remote_metrics
    from chatops.db import add_metric, add_alert, get_last_notified, set_last_notified
    from chatops.config import load_config
    from chatops.actions import notify_slack, alert_status as _alert_status
    from datetime import datetime, timezone, timedelta

    cfg = load_config()
    webhook = cfg.get("slack_webhook", "").strip()
    suppress_minutes = int(cfg.get("alert_suppress_minutes", 10))

    try:
        nodes = list_nodes()
    except Exception:
        return

    for node_name, node_info in nodes.items():
        if node_info.get("host") in ("127.0.0.1", "localhost"):
            continue
        try:
            metrics = get_remote_metrics(node_info)
            node_thresholds = node_info.get("thresholds") or {}
            for metric, pct in metrics.items():
                add_metric(metric, pct, node=node_name)
                warn = node_thresholds.get(f"{metric}_warning", cfg.get(f"{metric}_warning"))
                crit = node_thresholds.get(f"{metric}_critical", cfg.get(f"{metric}_critical"))
                status = _alert_status(pct, warn, crit)
                if status != "OK":
                    add_alert(
                        f"[{node_name}] {metric.capitalize()} {status}: {pct:.1f}%",
                        status, source=node_name, node=node_name,
                    )

                if status == "CRITICAL" and webhook:
                    suppress_key = f"{node_name}:{metric}"
                    last = get_last_notified(suppress_key)
                    should_notify = True
                    if last:
                        last_dt = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
                        now_dt = datetime.now(timezone.utc)
                        if (now_dt - last_dt).total_seconds() < suppress_minutes * 60:
                            should_notify = False
                    if should_notify:
                        ok, _ = notify_slack(webhook, metric, status, pct, node_name)
                        if ok:
                            set_last_notified(suppress_key)
        except Exception:
            pass


async def _health_check_loop():
    loop = asyncio.get_event_loop()
    while True:
        try:
            cfg = load_config()
            interval = int(cfg.get("health_check_interval", 60))
        except Exception:
            interval = 60
        try:
            await loop.run_in_executor(None, _health_check_sync)
        except Exception:
            pass
        try:
            await loop.run_in_executor(None, _poll_remote_nodes_sync)
        except Exception:
            pass
        await asyncio.sleep(interval)


async def _daily_report_loop():
    """Fire once per day at the configured hour and post a report to Slack."""
    import asyncio
    from datetime import datetime, timedelta
    loop = asyncio.get_event_loop()

    while True:
        try:
            cfg = load_config()
            if cfg.get("report_enabled"):
                now = datetime.now()
                target_hour = int(cfg.get("report_hour", 8))
                next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                cfg = load_config()
                if cfg.get("report_enabled"):
                    from chatops.actions import generate_report, format_report_slack, notify_slack
                    webhook = cfg.get("slack_webhook", "").strip()
                    report = await loop.run_in_executor(None, generate_report, 24)
                    if webhook:
                        text = format_report_slack(report)
                        import urllib.request, json as _json
                        payload = {"text": text}
                        data = _json.dumps(payload).encode("utf-8")
                        req = urllib.request.Request(
                            webhook, data=data,
                            headers={"Content-Type": "application/json"}, method="POST"
                        )
                        try:
                            urllib.request.urlopen(req, timeout=5)
                        except Exception:
                            pass
            else:
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    health_task  = asyncio.create_task(_health_check_loop())
    report_task  = asyncio.create_task(_daily_report_loop())
    yield
    health_task.cancel()
    report_task.cancel()


app = FastAPI(lifespan=lifespan)


# ── Auth helpers ───────────────────────────────────────────────────────────────

_security = HTTPBearer(auto_error=False)


def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def _require_role(min_role: str):
    level = ROLE_LEVEL[min_role]
    def _dep(user=Depends(_get_current_user)):
        if ROLE_LEVEL.get(user.get("role"), 0) < level:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _dep


# ── Request models ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str


class NodeThresholds(BaseModel):
    disk_warning:    float
    disk_critical:   float
    memory_warning:  float
    memory_critical: float
    cpu_warning:     float
    cpu_critical:    float


class ConfigUpdate(BaseModel):
    disk_warning: Optional[float] = None
    disk_critical: Optional[float] = None
    memory_warning: Optional[float] = None
    memory_critical: Optional[float] = None
    cpu_warning: Optional[float] = None
    cpu_critical: Optional[float] = None
    health_check_interval: Optional[int] = None
    slack_webhook: Optional[str] = None
    alert_suppress_minutes: Optional[int] = None
    report_enabled: Optional[bool] = None
    report_hour:    Optional[int]  = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "operator"


class UpdateRoleRequest(BaseModel):
    role: str


# ── ChatOps routes ─────────────────────────────────────────────────────────────

@app.get("/chatops", response_class=HTMLResponse)
async def chatops_page():
    path = pathlib.Path("chatops/static/chatops.html")
    if path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse("<html><body><h1>ChatOps</h1></body></html>")


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@app.post("/chatops/auth/login")
def login(req: LoginRequest):
    user = get_user(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(req.username, user["role"])
    return {"token": token, "username": req.username, "role": user["role"]}


@app.get("/chatops/auth/me")
def me(user=Depends(_get_current_user)):
    return {"username": user["sub"], "role": user["role"]}


@app.get("/chatops/auth/users")
def list_users_endpoint(user=Depends(_require_role("admin"))):
    return {"users": db_list_users()}


@app.post("/chatops/auth/users")
def create_user_endpoint(req: CreateUserRequest, user=Depends(_require_role("admin"))):
    if req.role not in ROLE_LEVEL:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose: {list(ROLE_LEVEL)}")
    ok = db_create_user(req.username, hash_password(req.password), req.role)
    if not ok:
        raise HTTPException(status_code=409, detail=f"User '{req.username}' already exists")
    return {"status": "ok", "username": req.username, "role": req.role}


@app.delete("/chatops/auth/users/{username}")
def deactivate_user_endpoint(username: str, user=Depends(_require_role("admin"))):
    if username == user["sub"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    ok = set_user_active(username, False)
    if not ok:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return {"status": "ok"}


@app.put("/chatops/auth/users/{username}/role")
def update_role_endpoint(username: str, req: UpdateRoleRequest, user=Depends(_require_role("admin"))):
    if req.role not in ROLE_LEVEL:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose: {list(ROLE_LEVEL)}")
    ok = update_user_role(username, req.role)
    if not ok:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return {"status": "ok"}


# ── Audit endpoint ─────────────────────────────────────────────────────────────

@app.get("/chatops/audit")
def get_audit_endpoint(
    limit: int = 50,
    username: str = None,
    node: str = None,
    user=Depends(_require_role("operator")),
):
    return {"audit_log": get_audit_log(limit=limit, username=username, node=node)}


@app.post("/chatops/message")
def chatops_message(msg: ChatMessage, user=Depends(_require_role("operator"))):
    save_message("user", msg.message)
    result = route_message(msg.message)
    save_message("bot", result.get("response", ""))
    add_audit(user["sub"], msg.message, (result.get("response") or "")[:200])
    return result


@app.get("/chatops/history")
def get_chat_history(limit: int = 50, user=Depends(_require_role("viewer"))):
    return {"history": get_history(limit)}


@app.delete("/chatops/history")
def clear_chat_history(user=Depends(_require_role("operator"))):
    clear_history()
    return {"status": "ok"}


@app.get("/chatops/alerts")
def get_alerts_endpoint(limit: int = 50, unacked_only: bool = False, node: str = None, user=Depends(_require_role("viewer"))):
    alerts = get_alerts(limit=limit, unacked_only=unacked_only, node=node)
    count = unacked_count(node=node)
    return {"alerts": alerts, "unacked_count": count}


@app.post("/chatops/alerts/{alert_id}/ack")
def ack_alert_endpoint(alert_id: int, user=Depends(_require_role("operator"))):
    ack_alert(alert_id)
    return {"status": "ok", "unacked_count": unacked_count()}


@app.get("/chatops/metrics/history")
def metrics_history_endpoint(metric: str = "disk", limit: int = 60, node: str = "local", user=Depends(_require_role("viewer"))):
    return {"metric": metric, "data": get_metric_history(metric, limit, node=node)}


@app.get("/chatops/nodes")
def get_nodes_endpoint(user=Depends(_require_role("viewer"))):
    from chatops.nodes import list_nodes
    nodes = [{"name": "local", "host": "this server", "user": "-", "key_path": "-"}]
    for name, info in list_nodes().items():
        if info.get("host") not in ("127.0.0.1", "localhost"):
            nodes.append({
                "name": name,
                "host": info["host"],
                "user": info.get("user", "ubuntu"),
                "key_path": info.get("key_path", "~/.ssh/id_rsa"),
            })
    return {"nodes": nodes}


@app.get("/chatops/nodes/{name}/config")
def get_node_config_endpoint(name: str, user=Depends(_require_role("viewer"))):
    from chatops.nodes import get_node
    global_cfg = load_config()
    defaults = {k: global_cfg[k] for k in (
        "disk_warning", "disk_critical", "memory_warning",
        "memory_critical", "cpu_warning", "cpu_critical",
    )}
    node = get_node(name)
    if not node:
        return {"thresholds": defaults, "is_default": True}
    thresholds = node.get("thresholds")
    if thresholds:
        return {"thresholds": thresholds, "is_default": False}
    return {"thresholds": defaults, "is_default": True}


@app.put("/chatops/nodes/{name}/config")
def set_node_config_endpoint(name: str, body: NodeThresholds, user=Depends(_require_role("admin"))):
    from chatops.nodes import set_node_thresholds
    ok = set_node_thresholds(name, body.model_dump())
    if not ok:
        raise HTTPException(status_code=404, detail=f"Node '{name}' not found")
    return {"status": "ok"}


@app.get("/chatops/report")
def get_report_endpoint(hours: int = 24, user=Depends(_require_role("viewer"))):
    from chatops.actions import generate_report
    return generate_report(hours)


@app.get("/chatops/config")
def get_config_endpoint(user=Depends(_require_role("viewer"))):
    return load_config()


@app.put("/chatops/config")
def update_config_endpoint(updates: ConfigUpdate, user=Depends(_require_role("admin"))):
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    return save_config(data)


@app.get("/chatops/runbooks")
def get_runbooks_endpoint(user=Depends(_require_role("viewer"))):
    return {"runbooks": list_runbooks()}


@app.post("/chatops/upload-log")
async def upload_log(file: UploadFile = File(...), user=Depends(_require_role("admin"))):
    content = await file.read()
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return {"response": "Could not read file. Please upload a plain text log file."}

    from chatops.actions import analyze_logs
    data = analyze_logs(text)
    actions = ", ".join(data.get("suggested_actions", []))
    response = (
        f"Log File: {file.filename}\n"
        f"Severity: {data['severity']} | "
        f"Root cause: {data['root_cause']} | "
        f"Impact: {data['impact']}\n"
        f"Actions: {actions}"
    )
    save_message("user", f"[uploaded] {file.filename}")
    save_message("bot", response)
    return {"response": response, "filename": file.filename}
