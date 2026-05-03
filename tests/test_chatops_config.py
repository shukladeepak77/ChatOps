from chatops.config import load_config, save_config, alert_status_from_config

_EXPECTED_KEYS = [
    "disk_warning", "disk_critical",
    "memory_warning", "memory_critical",
    "cpu_warning", "cpu_critical",
    "health_check_interval",
]


def test_load_config_defaults():
    cfg = load_config()
    for key in _EXPECTED_KEYS:
        assert key in cfg


def test_save_and_reload_config():
    save_config({"disk_warning": 75.0})
    assert load_config()["disk_warning"] == 75.0


def test_save_config_merges_defaults():
    save_config({"disk_warning": 75.0})
    cfg = load_config()
    assert cfg["disk_critical"] == 90.0
    assert cfg["memory_warning"] == 80.0


def test_alert_status_from_config_ok():
    assert alert_status_from_config(50.0, "disk") == "OK"


def test_alert_status_from_config_warning():
    assert alert_status_from_config(85.0, "disk") == "WARNING"


def test_alert_status_from_config_critical():
    assert alert_status_from_config(95.0, "disk") == "CRITICAL"
