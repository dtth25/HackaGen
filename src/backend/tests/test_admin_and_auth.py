import uuid
import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.core import db


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_admin_users.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setenv("CREATE_DEFAULT_ADMIN", "true")
    monkeypatch.setenv("ADMIN_EMAIL", "admin_test@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "secretAdminPass123!")
    db.init_db()
    yield


def test_admin_user_management_flow():
    with TestClient(main.app) as client:
        # 1. Login as default admin
        admin_login = client.post(
            "/auth/login",
            json={"email": "admin_test@example.com", "password": "secretAdminPass123!"},
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Register a regular user
        user_email = f"regular_{uuid.uuid4().hex[:8]}@example.com"
        reg_res = client.post(
            "/auth/register",
            json={"email": user_email, "password": "UserPass123!", "full_name": "Regular User"},
        )
        assert reg_res.status_code == 201
        user_data = reg_res.json()["user"]
        user_id = user_data["id"]
        user_token = reg_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 3. Regular user trying to access admin route should fail (403)
        unauth_list = client.get("/admin/users", headers=user_headers)
        assert unauth_list.status_code == 403

        # 4. Admin listing users should succeed (200) and show at least 2 users
        list_res = client.get("/admin/users", headers=admin_headers)
        assert list_res.status_code == 200
        users_list = list_res.json()
        assert len(users_list) >= 2
        assert all("password_hash" not in user for user in users_list)
        emails = [u["email"] for u in users_list]
        assert "admin_test@example.com" in emails
        assert user_email in emails

        # 5. Admin promoting regular user to admin
        make_admin_res = client.post(f"/admin/users/{user_id}/make-admin", headers=admin_headers)
        assert make_admin_res.status_code == 200
        assert make_admin_res.json()["role"] == "admin"

        # 6. Admin demoting user back to regular user
        make_user_res = client.post(f"/admin/users/{user_id}/make-user", headers=admin_headers)
        assert make_user_res.status_code == 200
        assert make_user_res.json()["role"] == "user"

        # 7. Try demoting the last remaining admin (admin_test@example.com) -> should fail (400)
        admin_user_obj = [u for u in users_list if u["email"] == "admin_test@example.com"][0]
        admin_id = admin_user_obj["id"]
        demote_last_res = client.post(f"/admin/users/{admin_id}/make-user", headers=admin_headers)
        assert demote_last_res.status_code == 400
        assert "quản trị viên duy nhất" in demote_last_res.json()["detail"].lower()

        # 8. Try disabling the last remaining admin -> should fail (400)
        disable_last_res = client.post(f"/admin/users/{admin_id}/disable", headers=admin_headers)
        assert disable_last_res.status_code == 400

        # 9. Try deleting the last remaining admin -> should fail (400)
        delete_last_res = client.delete(f"/admin/users/{admin_id}", headers=admin_headers)
        assert delete_last_res.status_code == 400

        # 10. Admin disabling regular user
        disable_res = client.post(f"/admin/users/{user_id}/disable", headers=admin_headers)
        assert disable_res.status_code == 200
        assert disable_res.json()["is_active"] is False

        # 11. Disabled user trying to call protected API (/auth/me) -> should fail (401 or 403)
        disabled_me = client.get("/auth/me", headers=user_headers)
        assert disabled_me.status_code in (401, 403)

        # 12. Admin enabling regular user
        enable_res = client.post(f"/admin/users/{user_id}/enable", headers=admin_headers)
        assert enable_res.status_code == 200
        assert enable_res.json()["is_active"] is True

        # 13. Enabled user can call /auth/me again
        enabled_me = client.get("/auth/me", headers=user_headers)
        assert enabled_me.status_code == 200

        # 14. Admin resetting regular user password
        reset_res = client.post(
            f"/admin/users/{user_id}/reset-password",
            headers=admin_headers,
            json={"new_password": "NewSecretPass123!"},
        )
        assert reset_res.status_code == 200

        # 15. User can login with new password
        new_login = client.post(
            "/auth/login",
            json={"email": user_email, "password": "NewSecretPass123!"},
        )
        assert new_login.status_code == 200

        # 16. Admin deleting regular user
        delete_res = client.delete(f"/admin/users/{user_id}", headers=admin_headers)
        assert delete_res.status_code == 200
        assert "thành công" in delete_res.json()["detail"].lower()

        # 17. Deleted user should not be found in list
        list_after = client.get("/admin/users", headers=admin_headers)
        assert user_email not in [u["email"] for u in list_after.json()]
