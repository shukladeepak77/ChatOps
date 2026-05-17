import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
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
    runbook_create, runbook_list, runbook_get, runbook_delete,
    netdev_add, netdev_get, netdev_list, netdev_delete,
    netdev_save_backup, netdev_get_backup, netdev_list_backups,
    netdev_log_interfaces,
    get_last_notified, set_last_notified,
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


def _poll_network_devices_sync():
    """Poll registered network devices — alert on interface down, BGP neighbor loss, or connection failure."""
    from datetime import datetime, timezone
    from chatops.db import netdev_log_interfaces
    from chatops.network import get_interfaces, get_bgp_neighbors
    _SUPPRESS_SECS = 1800  # re-alert at most every 30 minutes per condition

    def _suppressed(key: str) -> bool:
        last = get_last_notified(key)
        if not last:
            return False
        try:
            last_dt = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - last_dt).total_seconds() < _SUPPRESS_SECS
        except Exception:
            return False

    def _alert(key: str, msg: str, sev: str, source: str):
        if not _suppressed(key):
            add_alert(msg, sev, source=source)
            set_last_notified(key)

    try:
        devices = netdev_list()
    except Exception:
        return

    for dev_row in devices:
        full_dev = netdev_get(dev_row["name"])
        if not full_dev:
            continue
        name = dev_row["name"]
        dt   = full_dev.get("device_type", "cisco_xe")

        # ── Interface check ──────────────────────────────────────────────────
        try:
            result = get_interfaces(full_dev)
            if result["status"] == "error":
                _alert(f"{name}:connect", f"[{name}] Cannot connect: {result['error'][:120]}", "CRITICAL", name)
                continue
            ifaces = result["interfaces"]
            netdev_log_interfaces(name, ifaces)
            for iface in ifaces:
                st = (iface.get("status") or "").lower()
                # skip expected non-up states (admin-down, no cable, etc.)
                if st in ("up", "connected", "notconnect", "routed", "sfpabsent"):
                    continue
                _alert(
                    f"{name}:iface:{iface['interface']}",
                    f"[{name}] Interface {iface['interface']} is {iface.get('status','?')}",
                    "WARNING", name,
                )
        except Exception:
            pass

        # ── BGP neighbor check (Cisco only) ──────────────────────────────────
        if dt == "linux":
            continue
        try:
            bgp = get_bgp_neighbors(full_dev)
            if bgp.get("status") == "ok":
                for nbr in bgp.get("neighbors", []):
                    state = nbr.get("state", "")
                    if state != "Established":
                        _alert(
                            f"{name}:bgp:{nbr.get('neighbor','?')}",
                            f"[{name}] BGP neighbor {nbr.get('neighbor','?')} AS{nbr.get('as','?')} state={state or 'unknown'}",
                            "CRITICAL", name,
                        )
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
        try:
            from chatops.predictive import run_predictive_check
            await loop.run_in_executor(None, run_predictive_check)
        except Exception:
            pass
        try:
            await loop.run_in_executor(None, _poll_network_devices_sync)
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
    default_node:   Optional[str]  = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "operator"


class NetworkDeviceCreate(BaseModel):
    name:         str
    host:         str
    username:     str
    password:     str
    device_type:  str = "cisco_xe"
    port:         int = 22
    netconf_port: int = 830
    description:  str = ""


class NetworkConfigPush(BaseModel):
    commands: list


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
    result = route_message(msg.message, caller_role=user.get("role", "operator"))
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


@app.get("/chatops/test-log/{filename}")
def get_test_log(filename: str, user=Depends(_require_role("viewer"))):
    import re, os
    from fastapi.responses import PlainTextResponse
    if not re.fullmatch(r"pytest_\d{8}_\d{6}\.log", filename):
        raise HTTPException(status_code=400, detail="Invalid log filename")
    log_path = os.path.join(os.path.dirname(__file__), "sample_logs", filename)
    if not os.path.isfile(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    with open(log_path) as f:
        return PlainTextResponse(f.read())


@app.delete("/chatops/test-log/{filename}")
def delete_test_log(filename: str, user=Depends(_require_role("developer"))):
    import re, os
    if not re.fullmatch(r"pytest_\d{8}_\d{6}\.log", filename):
        raise HTTPException(status_code=400, detail="Invalid log filename")
    log_path = os.path.join(os.path.dirname(__file__), "sample_logs", filename)
    if not os.path.isfile(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    os.remove(log_path)
    return {"status": "deleted", "filename": filename}


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


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/chatops/analytics")
def get_analytics(days: int = 7, user=Depends(_require_role("viewer"))):
    from chatops.analytics import get_alert_stats, get_mttr_stats, get_command_stats
    return {
        "alert_stats": get_alert_stats(days),
        "mttr": get_mttr_stats(days),
        "top_commands": get_command_stats(days),
    }


@app.get("/chatops/analytics/report.pdf")
def download_pdf_report(days: int = 7, user=Depends(_require_role("viewer"))):
    from chatops.analytics import generate_pdf_report
    pdf_bytes = generate_pdf_report(days)
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=chatops_report_{days}d.pdf"},
    )


# ── Prometheus metrics ────────────────────────────────────────────────────────

@app.get("/chatops/metrics/prometheus")
def prometheus_metrics(user=Depends(_require_role("viewer"))):
    from fastapi.responses import PlainTextResponse
    from chatops.db import get_alerts, unacked_count, get_metric_history
    from chatops.analytics import get_alert_stats, get_mttr_stats, get_command_stats
    from chatops.actions import check_disk, check_memory, check_cpu
    import time

    lines = [
        "# HELP chatops_alerts_total Total alerts by severity",
        "# TYPE chatops_alerts_total gauge",
    ]
    stats = get_alert_stats(7)
    for sev, cnt in stats.get("by_severity", {}).items():
        lines.append(f'chatops_alerts_total{{severity="{sev}"}} {cnt}')
    lines += [
        "# HELP chatops_alerts_unacked Unacknowledged alerts",
        "# TYPE chatops_alerts_unacked gauge",
        f"chatops_alerts_unacked {unacked_count()}",
        "# HELP chatops_mttr_minutes_avg Average MTTR in minutes (last 7 days)",
        "# TYPE chatops_mttr_minutes_avg gauge",
    ]
    mttr = get_mttr_stats(7)
    lines.append(f"chatops_mttr_minutes_avg {mttr['avg_minutes'] if mttr['avg_minutes'] is not None else 'NaN'}")
    lines += [
        "# HELP chatops_system_usage_percent Current system resource usage",
        "# TYPE chatops_system_usage_percent gauge",
    ]
    try:
        lines.append(f'chatops_system_usage_percent{{resource="disk"}} {check_disk()["percent_used"]}')
    except Exception:
        pass
    try:
        lines.append(f'chatops_system_usage_percent{{resource="memory"}} {check_memory()["percent_used"]}')
    except Exception:
        pass
    try:
        lines.append(f'chatops_system_usage_percent{{resource="cpu"}} {check_cpu()["percent_used"]}')
    except Exception:
        pass
    lines += [
        "# HELP chatops_top_commands_total Command usage count (last 7 days)",
        "# TYPE chatops_top_commands_total gauge",
    ]
    for cmd in get_command_stats(7)[:10]:
        safe = cmd["command"].replace('"', '\\"')
        lines.append(f'chatops_top_commands_total{{command="{safe}"}} {cmd["count"]}')
    lines.append(f"\n# Generated at {int(time.time())}")
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


# ── Knowledge Base REST API ───────────────────────────────────────────────────

class KBArticleRequest(BaseModel):
    title: str
    content: str
    tags: str = ""

@app.get("/chatops/kb")
def kb_list_endpoint(user=Depends(_require_role("viewer"))):
    from chatops.db import kb_list
    return {"articles": kb_list()}

@app.get("/chatops/kb/{article_id}")
def kb_get_endpoint(article_id: int, user=Depends(_require_role("viewer"))):
    from chatops.db import kb_get
    article = kb_get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@app.post("/chatops/kb")
def kb_create_endpoint(req: KBArticleRequest, user=Depends(_require_role("operator"))):
    from chatops.db import kb_add
    aid = kb_add(req.title, req.content, tags=req.tags, created_by=user.get("username", "admin"))
    return {"id": aid, "title": req.title}

@app.delete("/chatops/kb/{article_id}")
def kb_delete_endpoint(article_id: int, user=Depends(_require_role("admin"))):
    from chatops.db import kb_delete
    if not kb_delete(article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "deleted", "id": article_id}


# ── Slack inbound bot ─────────────────────────────────────────────────────────

@app.post("/chatops/slack/events")
async def slack_events(request: Request):
    import hmac, hashlib, json as _json, time as _time
    from chatops.config import load_config as _cfg

    body = await request.body()
    cfg = _cfg()
    signing_secret = cfg.get("slack_signing_secret", "")

    if signing_secret:
        ts = request.headers.get("X-Slack-Request-Timestamp", "")
        sig = request.headers.get("X-Slack-Signature", "")
        if abs(_time.time() - int(ts or 0)) > 300:
            raise HTTPException(status_code=403, detail="Request too old")
        base = f"v0:{ts}:{body.decode()}"
        expected = "v0=" + hmac.new(signing_secret.encode(), base.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=403, detail="Invalid signature")

    payload = _json.loads(body)

    # URL verification challenge (one-time during app setup)
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    event = payload.get("event", {})
    etype = event.get("type", "")
    if etype not in ("message", "app_mention"):
        return {"ok": True}
    if event.get("bot_id") or event.get("subtype"):
        return {"ok": True}

    text = event.get("text", "").strip()
    channel = event.get("channel", "")
    bot_token = cfg.get("slack_bot_token", "")
    if not text or not bot_token:
        return {"ok": True}

    # Strip bot mention if present (e.g. <@U12345> check disk)
    import re as _re
    text = _re.sub(r"<@\w+>\s*", "", text).strip()

    result = route_message(text, caller_role="operator")
    reply = result.get("response", "Sorry, I didn't understand that.")

    import urllib.request as _ur, urllib.error as _ue
    import json as _j
    payload_out = _j.dumps({"channel": channel, "text": reply}).encode()
    req = _ur.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload_out,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {bot_token}"},
        method="POST",
    )
    try:
        _ur.urlopen(req, timeout=10)
    except _ue.URLError:
        pass


# ── Webhook ingestion: PagerDuty ──────────────────────────────────────────────

@app.post("/chatops/webhooks/pagerduty")
async def pagerduty_webhook(request: Request):
    import json as _j
    body = await request.body()
    try:
        payload = _j.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    messages = payload.get("messages") or []
    if not messages:
        # v3 envelope
        messages = [payload]

    created = []
    for msg in messages:
        event = msg.get("event", {})
        data  = event.get("data", {})
        title = data.get("title") or msg.get("message", {}).get("summary", "PagerDuty alert")
        sev_map = {"critical": "CRITICAL", "error": "ERROR", "warning": "WARNING", "info": "INFO"}
        sev = sev_map.get((data.get("severity") or "info").lower(), "INFO")
        alert_id = add_alert(title, sev, source="pagerduty")
        created.append(alert_id)

    return {"received": len(created), "alert_ids": created}


# ── Webhook ingestion: Datadog ────────────────────────────────────────────────

@app.post("/chatops/webhooks/datadog")
async def datadog_webhook(request: Request):
    import json as _j
    body = await request.body()
    try:
        payload = _j.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    title = payload.get("title") or payload.get("event_title") or "Datadog alert"
    sev_raw = (payload.get("alert_type") or payload.get("priority") or "info").lower()
    sev_map = {"error": "CRITICAL", "warning": "WARNING", "info": "INFO", "success": "INFO"}
    sev = sev_map.get(sev_raw, "INFO")
    alert_id = add_alert(title, sev, source="datadog")

    return {"received": 1, "alert_id": alert_id}


# ── Custom Runbooks CRUD ───────────────────────────────────────────────────────

class RunbookCreate(BaseModel):
    name: str
    description: str = ""
    steps: str = "[]"


@app.get("/chatops/custom-runbooks")
def list_custom_runbooks(user=Depends(_get_current_user)):
    return runbook_list()


@app.post("/chatops/custom-runbooks")
def create_custom_runbook(req: RunbookCreate, user=Depends(_require_role("operator"))):
    import json as _j
    try:
        steps_parsed = _j.loads(req.steps)
        if not isinstance(steps_parsed, list):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="steps must be a JSON array")
    try:
        rb_id = runbook_create(req.name, req.description, req.steps, created_by=user["sub"])
    except Exception:
        raise HTTPException(status_code=409, detail="A runbook with that name already exists")
    add_audit(user["sub"], f"runbook create {req.name}")
    return {"id": rb_id, "name": req.name}


@app.delete("/chatops/custom-runbooks/{name}")
def delete_custom_runbook(name: str, user=Depends(_require_role("admin"))):
    if not runbook_delete(name):
        raise HTTPException(status_code=404, detail="Runbook not found")
    add_audit(user["sub"], f"runbook delete {name}")
    return {"deleted": name}


# ── Network Device Management ─────────────────────────────────────────────────

@app.get("/chatops/network/devices")
def list_network_devices(user=Depends(_get_current_user)):
    return netdev_list()


@app.post("/chatops/network/devices")
def add_network_device(req: NetworkDeviceCreate, user=Depends(_require_role("operator"))):
    from chatops.network import encode_password
    if netdev_get(req.name):
        raise HTTPException(status_code=409, detail="Device name already exists")
    did = netdev_add(
        req.name, req.host, req.username, encode_password(req.password),
        device_type=req.device_type, port=req.port,
        netconf_port=req.netconf_port, description=req.description,
        created_by=user["sub"],
    )
    add_audit(user["sub"], f"network device add {req.name} {req.host}")
    return {"id": did, "name": req.name, "host": req.host, "device_type": req.device_type}


@app.delete("/chatops/network/devices/{name}")
def remove_network_device(name: str, user=Depends(_require_role("admin"))):
    if not netdev_delete(name):
        raise HTTPException(status_code=404, detail="Device not found")
    add_audit(user["sub"], f"network device remove {name}")
    return {"deleted": name}


@app.get("/chatops/network/devices/{name}/info")
def network_device_info(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_device_info
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_device_info(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/interfaces")
def network_device_interfaces(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_interfaces
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_interfaces(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    netdev_log_interfaces(name, result["interfaces"])
    return result


@app.get("/chatops/network/devices/{name}/routes")
def network_device_routes(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_routes
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_routes(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/bgp")
def network_device_bgp(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_bgp_neighbors
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_bgp_neighbors(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/cpu")
def network_device_cpu(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_cpu_memory
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_cpu_memory(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.post("/chatops/network/devices/{name}/backup")
def network_device_backup(name: str, user=Depends(_require_role("operator"))):
    from chatops.network import backup_config
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = backup_config(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    bid = netdev_save_backup(name, result["config"], result["lines"])
    add_audit(user["sub"], f"network backup {name}")
    return {"backup_id": bid, "device": name, "lines": result["lines"]}


@app.get("/chatops/network/devices/{name}/backups")
def network_device_backup_list(name: str, user=Depends(_get_current_user)):
    if not netdev_get(name):
        raise HTTPException(status_code=404, detail="Device not found")
    return netdev_list_backups(name)


@app.get("/chatops/network/devices/{name}/backups/latest")
def network_device_backup_latest(name: str, user=Depends(_get_current_user)):
    bk = netdev_get_backup(name)
    if not bk:
        raise HTTPException(status_code=404, detail="No backup found")
    return bk


@app.post("/chatops/network/devices/{name}/push-config")
def network_device_push_config(name: str, req: NetworkConfigPush,
                                user=Depends(_require_role("admin"))):
    from chatops.network import push_config
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = push_config(dev, req.commands)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    add_audit(user["sub"], f"network push-config {name}: {len(req.commands)} commands")
    return result


@app.get("/chatops/network/devices/{name}/config-diff")
def network_config_diff(name: str, user=Depends(_get_current_user)):
    """Diff running-config vs last stored backup."""
    from chatops.network import get_config_diff
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_config_diff(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/alerts")
def network_alerts(limit: int = 100, unacked_only: bool = False, user=Depends(_get_current_user)):
    """Return alerts whose source matches a registered network device."""
    device_names = {d["name"] for d in netdev_list()}
    all_alerts = get_alerts(limit=limit * 4, unacked_only=unacked_only)
    net_alerts = [a for a in all_alerts if a.get("source") in device_names][:limit]
    return {"alerts": net_alerts, "total": len(net_alerts)}


@app.post("/chatops/network/alerts/{alert_id}/ack")
def network_ack_alert(alert_id: int, user=Depends(_require_role("operator"))):
    ack_alert(alert_id)
    return {"status": "ok"}


@app.get("/chatops/network/devices/{name}/arp")
def network_device_arp(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_arp_table
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_arp_table(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/ping")
def network_device_ping(name: str, target: str = "8.8.8.8", user=Depends(_get_current_user)):
    from chatops.network import ping_device
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = ping_device(dev, target=target)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/ospf")
def network_device_ospf(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_ospf_neighbors
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_ospf_neighbors(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/logs")
def network_device_logs(name: str, lines: int = 50, user=Depends(_get_current_user)):
    from chatops.network import get_logs
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_logs(dev, lines=lines)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/traceroute")
def network_device_traceroute(name: str, target: str, user=Depends(_get_current_user)):
    from chatops.network import run_traceroute
    if not target:
        raise HTTPException(status_code=400, detail="target query parameter required")
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = run_traceroute(dev, target=target)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/cdp")
def network_device_cdp(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_cdp_neighbors
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_cdp_neighbors(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/errors")
def network_device_errors(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_interface_errors
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_interface_errors(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/devices/{name}/mac-table")
def network_device_mac_table(name: str, user=Depends(_get_current_user)):
    from chatops.network import get_mac_table
    dev = netdev_get(name)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    result = get_mac_table(dev)
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@app.get("/chatops/network/dashboard")
def network_dashboard(user=Depends(_get_current_user)):
    """Fetch device info + CPU for all registered devices in parallel."""
    from chatops.network import get_device_info, get_cpu_memory
    from concurrent.futures import ThreadPoolExecutor, as_completed

    devs = netdev_list()

    def fetch_one(dev):
        name = dev["name"]
        try:
            full_dev = netdev_get(name) or dev
            info = get_device_info(full_dev)
            cpu  = get_cpu_memory(full_dev)
            ok   = info["status"] == "ok"
            return {
                "name":        name,
                "host":        dev["host"],
                "device_type": dev.get("device_type", "cisco_xe"),
                "reachable":   ok,
                "hostname":    info.get("hostname", "—") if ok else "—",
                "version":     info.get("version",  "—") if ok else "—",
                "uptime":      info.get("uptime",   "—") if ok else "—",
                "model":       info.get("model",    "—") if ok else "—",
                "cpu_5sec":    cpu.get("cpu_5sec",       "—") if cpu.get("status") == "ok" else "—",
                "mem_used":    cpu.get("mem_used_bytes", "—") if cpu.get("status") == "ok" else "—",
                "mem_free":    cpu.get("mem_free_bytes", "—") if cpu.get("status") == "ok" else "—",
                "error":       info.get("error") if not ok else None,
            }
        except Exception as e:
            return {
                "name": name, "host": dev["host"],
                "device_type": dev.get("device_type", "cisco_xe"),
                "reachable": False, "error": str(e),
                "hostname": "—", "version": "—", "uptime": "—",
                "model": "—", "cpu_5sec": "—", "mem_used": "—", "mem_free": "—",
            }

    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(fetch_one, dev): dev["name"] for dev in devs}
        for f in as_completed(futures, timeout=90):
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"name": futures[f], "reachable": False, "error": str(e)})

    return {"devices": results}


@app.post("/chatops/network/ping-matrix")
def network_ping_matrix(user=Depends(_get_current_user)):
    """Ping every device from every other device — returns reachability matrix.

    One thread per source device; targets are pinged sequentially within that
    thread.  This avoids opening multiple concurrent SSH sessions to the same
    device (IOS-XRv enforces a low session limit, causing random failures when
    all N pings fan out in parallel).
    """
    from chatops.network import ping_device
    from concurrent.futures import ThreadPoolExecutor, as_completed

    devs = netdev_list()
    names = [d["name"] for d in devs]
    dev_map = {d["name"]: d for d in devs}

    def run_from_src(src_name):
        src_dev = netdev_get(src_name) or dev_map[src_name]
        results = {}
        for tgt_name in [n for n in names if n != src_name]:
            try:
                result = ping_device(src_dev, target=dev_map[tgt_name]["host"], count=3)
                raw_rate = result.get("success_rate", "0")
                rate = int(raw_rate) if result["status"] == "ok" and str(raw_rate).isdigit() else 0
            except Exception:
                rate = -1
            results[tgt_name] = {"success_rate": rate, "reachable": rate > 0}
        return src_name, results

    matrix = {n: {} for n in names}

    with ThreadPoolExecutor(max_workers=len(names)) as ex:
        futures = {ex.submit(run_from_src, name): name for name in names}
        for f in as_completed(futures, timeout=180):
            try:
                src, row = f.result()
                matrix[src] = row
            except Exception:
                src = futures[f]
                matrix[src] = {t: {"success_rate": -1, "reachable": False} for t in names if t != src}

    return {"devices": names, "matrix": matrix}
