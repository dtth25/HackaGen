"""Automated tests for Core Infrastructure, Authentication, and CORS."""

from app.core.config import settings


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_register_and_me(client):
    # 1. Register new user
    reg_data = {
        "email": "testuser@example.com",
        "password": "secretpassword123",
        "full_name": "Test User",
    }
    response = client.post("/api/auth/register", json=reg_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["role"] == "user"

    # Check HttpOnly cookie is set
    assert settings.AUTH_COOKIE_NAME in response.cookies

    # 2. Get current user with Bearer token
    token = data["access_token"]
    me_response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "testuser@example.com"


def test_auth_login_and_cookie_flow(client):
    # Setup user
    reg_data = {
        "email": "loginuser@example.com",
        "password": "loginpassword123",
        "full_name": "Login User",
    }
    client.post("/api/auth/register", json=reg_data)

    # 1. Login with credentials
    login_data = {
        "email": "loginuser@example.com",
        "password": "loginpassword123",
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Check cookie
    cookie_val = response.cookies.get(settings.AUTH_COOKIE_NAME)
    assert cookie_val is not None

    # 2. Get me using ONLY the HttpOnly cookie (no Authorization header)
    client.cookies.set(settings.AUTH_COOKIE_NAME, cookie_val)
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "loginuser@example.com"


def test_auth_logout_blacklist(client):
    # Setup and login
    reg_data = {
        "email": "logoutuser@example.com",
        "password": "password123",
    }
    res = client.post("/api/auth/register", json=reg_data)
    token = res.json()["access_token"]

    # Verify access works
    assert (
        client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 200
    )

    # Logout
    logout_res = client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["detail"] == "Đăng xuất thành công."

    # Verify token is now blacklisted and rejected
    me_after_logout = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_after_logout.status_code == 401
    assert "Phiên đăng nhập đã bị hủy" in me_after_logout.json()["detail"]


def test_cors_headers(client):
    # Test preflight OPTIONS request
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    response = client.options("/api/auth/login", headers=headers)
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "http://localhost:3000"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"
