import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend import main
from backend.core import db


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_users.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield


def test_auth_register_login_flow():
    with TestClient(main.app) as client:
        unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "SuperSecretPassword123!"

        # 1. Register new user
        reg_response = client.post(
            "/auth/register",
            json={"email": unique_email, "password": password, "full_name": "Test User"},
        )
        assert reg_response.status_code == 201, reg_response.text
        reg_data = reg_response.json()
        assert "access_token" in reg_data
        assert reg_data["user"]["email"] == unique_email
        assert reg_data["user"]["role"] == "user"
        assert "password_hash" not in reg_data["user"]
        assert "set-cookie" in reg_response.headers
        assert "agy_session=" in reg_response.headers["set-cookie"]

        token = reg_data["access_token"]

        # 2. Duplicate registration should fail
        dup_response = client.post(
            "/auth/register",
            json={"email": unique_email, "password": password},
        )
        assert dup_response.status_code in (400, 409)

        # 3. Login with credentials
        login_response = client.post(
            "/auth/login",
            json={"email": unique_email, "password": password},
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data

        # 4. Login with wrong password should fail
        wrong_login = client.post(
            "/auth/login",
            json={"email": unique_email, "password": "WrongPassword!"},
        )
        assert wrong_login.status_code in (400, 401)

        # 5. Get current profile (/auth/me)
        headers = {"Authorization": f"Bearer {token}"}
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == unique_email
        assert me_data["full_name"] == "Test User"
        assert "password_hash" not in me_data

        # 6. Same client can authenticate via HttpOnly cookie without bearer header.
        cookie_me = client.get("/auth/me")
        assert cookie_me.status_code == 200
        assert cookie_me.json()["email"] == unique_email

        # 7. Logout clears cookie; unauthenticated /auth/me should return 401.
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200
        unauth_me = client.get("/auth/me")
        assert unauth_me.status_code == 401


def test_course_access_requires_owner_or_admin(monkeypatch):
    user = main.UserInDB(
        id="user_a",
        email="user_a@example.com",
        password_hash="pwd",
        role="user",
        is_active=True,
    )
    admin = main.UserInDB(
        id="admin",
        email="admin@example.com",
        password_hash="pwd",
        role="admin",
        is_active=True,
    )

    monkeypatch.setattr(main, "_course_owner_id", lambda course_id: "user_b")
    with pytest.raises(HTTPException) as denied:
        main._verify_course_access("private_doc", user)
    assert denied.value.status_code == 403

    monkeypatch.setattr(main, "_course_owner_id", lambda course_id: "user_a")
    main._verify_course_access("private_doc", user)
    main._verify_course_access("private_doc", admin)
