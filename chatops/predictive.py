"""
Predictive alerting: analyse recent metric trends and fire early-warning alerts
when a metric is projected to breach its threshold within the next 10 minutes.
"""
from datetime import datetime


def _linear_trend(values: list[float]) -> float:
    """Return slope (units per sample) via least-squares on evenly-spaced samples."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def check_predictive_alerts(node: str = "local") -> list[dict]:
    """
    Returns a list of predictive alert dicts for metrics trending toward a threshold.
    Each dict: {metric, current, projected, threshold_type, threshold_value, eta_minutes}
    """
    from .db import get_metric_history, _conn
    from .config import load_config

    cfg = load_config()
    fired = []

    for metric in ("disk", "memory", "cpu"):
        warn_threshold = float(cfg.get(f"{metric}_warning", 80))
        crit_threshold = float(cfg.get(f"{metric}_critical", 90))

        # Get last 30 samples (covers ~30 min at 60 s interval)
        history = get_metric_history(metric, limit=30, node=node)
        if len(history) < 5:
            continue

        values = [r["value"] for r in history]
        current = values[-1]

        # Skip if already above threshold — real alert already fired
        if current >= warn_threshold:
            continue

        slope = _linear_trend(values)
        if slope <= 0:
            continue  # trending down or flat — no concern

        # How many samples until we hit warning threshold?
        samples_to_warn = (warn_threshold - current) / slope
        samples_to_crit = (crit_threshold - current) / slope

        # Each sample ≈ health_check_interval seconds (default 60 s)
        interval_s = int(cfg.get("health_check_interval", 60))
        eta_warn_min = round(samples_to_warn * interval_s / 60, 1)
        eta_crit_min = round(samples_to_crit * interval_s / 60, 1)

        if eta_warn_min <= 10:
            fired.append({
                "metric": metric,
                "current": round(current, 1),
                "projected": round(current + slope * (10 * 60 / interval_s), 1),
                "threshold_type": "WARNING" if eta_crit_min > 10 else "CRITICAL",
                "threshold_value": warn_threshold if eta_crit_min > 10 else crit_threshold,
                "eta_minutes": eta_warn_min,
            })

    return fired


def run_predictive_check(node: str = "local"):
    """
    Called from the health-check loop. Fires predictive alerts into the DB
    using the configured alert_suppress_minutes window (default 30 min).
    """
    from .db import add_alert, get_last_notified, set_last_notified
    from .config import load_config
    from datetime import datetime, timedelta

    cfg = load_config()
    suppress_minutes = int(cfg.get("alert_suppress_minutes", 30))

    alerts = check_predictive_alerts(node)
    for a in alerts:
        metric = a["metric"]
        suppress_key = f"predictive_{metric}_{node}"

        last = get_last_notified(suppress_key)
        if last:
            try:
                last_dt = datetime.strptime(last[:19], "%Y-%m-%d %H:%M:%S")
                if datetime.utcnow() - last_dt < timedelta(minutes=suppress_minutes):
                    continue
            except Exception:
                pass

        msg = (
            f"[PREDICTIVE] {metric.capitalize()} trending toward "
            f"{a['threshold_type']} — currently {a['current']}%, "
            f"projected {a['projected']}% in ~{a['eta_minutes']} min "
            f"(threshold: {a['threshold_value']}%)"
        )
        add_alert(msg, f"PREDICTIVE_{a['threshold_type']}", source="predictive", node=node)
        set_last_notified(suppress_key)
