import json
import os

_DEFAULTS = {
    "disk_warning": 80.0,
    "disk_critical": 90.0,
    "memory_warning": 80.0,
    "memory_critical": 90.0,
    "cpu_warning": 70.0,
    "cpu_critical": 85.0,
    "health_check_interval": 60,
    "slack_webhook": "",
    "alert_suppress_minutes": 10,
    "report_enabled": False,
    "report_hour": 8,
    "llm_provider": "none",
    "llm_model": "",
    "llm_api_key": "",
    "ollama_url": "http://localhost:11434",
}

_CONFIG_FILE = "chatops_config.json"


def load_config() -> dict:
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE) as f:
                data = json.load(f)
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def save_config(updates: dict) -> dict:
    current = load_config()
    merged = {**current, **updates}
    with open(_CONFIG_FILE, "w") as f:
        json.dump(merged, f, indent=2)
    return merged


def alert_status_from_config(percent: float, metric: str) -> str:
    cfg = load_config()
    critical = cfg.get(f"{metric}_critical", 90.0)
    warning = cfg.get(f"{metric}_warning", 80.0)
    if percent >= critical:
        return "CRITICAL"
    if percent >= warning:
        return "WARNING"
    return "OK"
