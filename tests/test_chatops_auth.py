import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    async def _noop():
        pass
    import app as app_module
    monkeypatch.setattr(app_module, "_health_check_loop", _noop)
    monkeypatch.setattr(app_module, "_daily_report_loop", _noop)
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_client(client):
    resp = client.post("/chatops/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── Login ──────────────────────────────────────────────────────────────────────

def test_login_success(client):
    resp = client.post("/chatops/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_login_wrong_password(client):
    resp = client.post("/chatops/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/chatops/auth/login", json={"username": "nobody", "password": "pass"})
    assert resp.status_code == 401


# ── /auth/me ──────────────────────────────────────────────────────────────────

def test_me_with_valid_token(client):
    login_resp = client.post("/chatops/auth/login", json={"username": "admin", "password": "admin"})
    token = login_resp.json()["token"]
    resp = client.get("/chatops/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_me_with_no_token(client):
    resp = client.get("/chatops/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token(client):
    resp = client.get("/chatops/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


# ── Protected endpoints without auth ──────────────────────────────────────────

def test_message_without_auth(client):
    resp = client.post("/chatops/message", json={"message": "check disk"})
    assert resp.status_code == 401


def test_config_without_auth(client):
    resp = client.get("/chatops/config")
    assert resp.status_code == 401


# ── Role-based access ─────────────────────────────────────────────────────────

def _get_token(client, username, password):
    resp = client.post("/chatops/auth/login", json={"username": username, "password": password})
    return resp.json()["token"]


def test_viewer_can_get_config(admin_client):
    # Create a viewer user
    admin_client.post("/chatops/auth/users", json={"username": "viewer1", "password": "vpass", "role": "viewer"})
    token = _get_token(admin_client, "viewer1", "vpass")
    resp = admin_client.get("/chatops/config", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_viewer_cannot_post_message(admin_client):
    # Create a viewer user (may already exist from previous test in same run, ignore conflict)
    admin_client.post("/chatops/auth/users", json={"username": "viewer2", "password": "vpass2", "role": "viewer"})
    token = _get_token(admin_client, "viewer2", "vpass2")
    resp = admin_client.post(
        "/chatops/message",
        json={"message": "check disk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Admin user management ─────────────────────────────────────────────────────

def test_admin_can_list_users(admin_client):
    resp = admin_client.get("/chatops/auth/users")
    assert resp.status_code == 200
    users = resp.json()["users"]
    assert isinstance(users, list)
    assert any(u["username"] == "admin" for u in users)


def test_admin_can_create_user_who_can_login_and_send_messages(admin_client):
    # Create operator user
    resp = admin_client.post(
        "/chatops/auth/users",
        json={"username": "op_test", "password": "oppass", "role": "operator"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "op_test"
    assert data["role"] == "operator"

    # Operator can login
    token = _get_token(admin_client, "op_test", "oppass")
    assert token

    # Operator can send messages
    resp = admin_client.post(
        "/chatops/message",
        json={"message": "check disk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "Disk" in resp.json()["response"]


def test_create_duplicate_user_returns_409(admin_client):
    admin_client.post(
        "/chatops/auth/users",
        json={"username": "dup_user", "password": "pass", "role": "operator"},
    )
    resp = admin_client.post(
        "/chatops/auth/users",
        json={"username": "dup_user", "password": "pass", "role": "operator"},
    )
    assert resp.status_code == 409


def test_deactivate_user_cannot_login(admin_client):
    # Create user
    admin_client.post(
        "/chatops/auth/users",
        json={"username": "to_deactivate", "password": "dpass", "role": "operator"},
    )
    # Deactivate
    resp = admin_client.delete("/chatops/auth/users/to_deactivate")
    assert resp.status_code == 200

    # Deactivated user cannot login
    resp = admin_client.post(
        "/chatops/auth/login",
        json={"username": "to_deactivate", "password": "dpass"},
    )
    assert resp.status_code == 401


def test_update_role(admin_client):
    admin_client.post(
        "/chatops/auth/users",
        json={"username": "role_change", "password": "rpass", "role": "viewer"},
    )
    resp = admin_client.put(
        "/chatops/auth/users/role_change/role",
        json={"role": "operator"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify role was updated
    users = admin_client.get("/chatops/auth/users").json()["users"]
    user = next(u for u in users if u["username"] == "role_change")
    assert user["role"] == "operator"


def test_non_admin_cannot_create_user(admin_client):
    # Create a viewer
    admin_client.post(
        "/chatops/auth/users",
        json={"username": "non_admin_viewer", "password": "vpass", "role": "viewer"},
    )
    token = _get_token(admin_client, "non_admin_viewer", "vpass")
    resp = admin_client.post(
        "/chatops/auth/users",
        json={"username": "another_user", "password": "pass", "role": "operator"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Audit log ─────────────────────────────────────────────────────────────────

def test_audit_log_records_commands(admin_client):
    # Send a message
    admin_client.post("/chatops/message", json={"message": "check cpu"})

    # Check audit log
    resp = admin_client.get("/chatops/audit")
    assert resp.status_code == 200
    entries = resp.json()["audit_log"]
    assert isinstance(entries, list)
    assert len(entries) >= 1
    assert any(e["command"] == "check cpu" for e in entries)
    assert any(e["username"] == "admin" for e in entries)


def test_audit_log_requires_auth(client):
    resp = client.get("/chatops/audit")
    assert resp.status_code == 401
