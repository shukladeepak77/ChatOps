import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import pathlib

from chatops.router import route_message
from chatops.db import (
    init_db, save_message, get_history, clear_history,
    get_alerts, ack_alert, unacked_count, get_metric_history, add_alert,
)
from chatops.config import load_config, save_config
from chatops.runbooks import list_runbooks


# ── Background health check ───────────────────────────────────────────────────

def _health_check_sync():
    from chatops.actions import check_disk, check_memory, check_cpu
    from chatops.config import alert_status_from_config
    from chatops.db import add_metric

    for fn, metric in [(check_disk, "disk"), (check_memory, "memory"), (check_cpu, "cpu")]:
        try:
            data = fn()
            pct = data["percent_used"]
            add_metric(metric, pct)
            status = alert_status_from_config(pct, metric)
            if status != "OK":
                add_alert(f"{metric.capitalize()} {status}: {pct:.1f}% used", status)
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
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_health_check_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


# ── Request models ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str


class ConfigUpdate(BaseModel):
    disk_warning: Optional[float] = None
    disk_critical: Optional[float] = None
    memory_warning: Optional[float] = None
    memory_critical: Optional[float] = None
    cpu_warning: Optional[float] = None
    cpu_critical: Optional[float] = None
    health_check_interval: Optional[int] = None


# ── ChatOps routes ─────────────────────────────────────────────────────────────

@app.get("/chatops", response_class=HTMLResponse)
async def chatops_page():
    path = pathlib.Path("chatops/static/chatops.html")
    if path.exists():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse("<html><body><h1>ChatOps</h1></body></html>")


@app.post("/chatops/message")
def chatops_message(msg: ChatMessage):
    save_message("user", msg.message)
    result = route_message(msg.message)
    save_message("bot", result.get("response", ""))
    return result


@app.get("/chatops/history")
def get_chat_history(limit: int = 50):
    return {"history": get_history(limit)}


@app.delete("/chatops/history")
def clear_chat_history():
    clear_history()
    return {"status": "ok"}


@app.get("/chatops/alerts")
def get_alerts_endpoint(limit: int = 50, unacked_only: bool = False):
    alerts = get_alerts(limit=limit, unacked_only=unacked_only)
    count = unacked_count()
    return {"alerts": alerts, "unacked_count": count}


@app.post("/chatops/alerts/{alert_id}/ack")
def ack_alert_endpoint(alert_id: int):
    ack_alert(alert_id)
    return {"status": "ok", "unacked_count": unacked_count()}


@app.get("/chatops/metrics/history")
def metrics_history_endpoint(metric: str = "disk", limit: int = 60):
    return {"metric": metric, "data": get_metric_history(metric, limit)}


@app.get("/chatops/config")
def get_config_endpoint():
    return load_config()


@app.put("/chatops/config")
def update_config_endpoint(updates: ConfigUpdate):
    data = {k: v for k, v in updates.model_dump().items() if v is not None}
    return save_config(data)


@app.get("/chatops/runbooks")
def get_runbooks_endpoint():
    return {"runbooks": list_runbooks()}


@app.post("/chatops/upload-log")
async def upload_log(file: UploadFile = File(...)):
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
