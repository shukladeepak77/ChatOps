import pytest
import chatops.db as db_module
import chatops.config as config_module
import chatops.runbooks as runbooks_module


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "chatops_test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    db_module.init_db()
    yield db_file


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    cfg_file = str(tmp_path / "chatops_test_config.json")
    monkeypatch.setattr(config_module, "_CONFIG_FILE", cfg_file)
    yield cfg_file


@pytest.fixture(autouse=True)
def reset_runbook_state(monkeypatch):
    monkeypatch.setattr(runbooks_module, "_pending", None)
    yield
