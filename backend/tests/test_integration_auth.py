"""
Integration Tests: Auth Endpoints
====================================
Tests for POST /register, POST /login, GET /me, POST /change-password.

Fixtures from conftest.py:
  - test_client   — FastAPI AsyncClient (in-memory MongoDB)
  - test_user     — pre-created regular user
  - auth_headers  — Bearer token headers for test_user
"""

import pytest


# ================================================================
# POST /api/v1/auth/register
# ================================================================

class TestRegister:
    async def test_register_success(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "Password123!", "full_name": "New User"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data

    async def test_register_email_normalised_to_lowercase(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "UPPER@Example.COM", "password": "Password123!"},
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "upper@example.com"

    async def test_register_duplicate_email_returns_409(self, test_client, test_user):
        resp = await test_client.post(
            "/api/v1/auth/register",
            json={"email": test_user.email, "password": "AnotherPass1!"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    async def test_register_short_password_rejected(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "short"},
        )
        # Pydantic min_length=8 → 422 Unprocessable Entity
        assert resp.status_code == 422

    async def test_register_missing_email_rejected(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/auth/register",
            json={"password": "Password123!"},
        )
        assert resp.status_code == 422


# ================================================================
# POST /api/v1/auth/login
# ================================================================

class TestLogin:
    async def test_login_success_returns_token(self, test_client, test_user):
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "Password123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)

    async def test_login_wrong_password_returns_401(self, test_client, test_user):
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_email_returns_401(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "Password123!"},
        )
        assert resp.status_code == 401

    async def test_login_deactivated_user_returns_403(self, test_client, test_user):
        # Deactivate the user
        test_user.is_active = False
        await test_user.save()

        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "Password123!"},
        )
        assert resp.status_code == 403

    async def test_login_email_case_insensitive(self, test_client, test_user):
        """Login should work regardless of email casing."""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email.upper(), "password": "Password123!"},
        )
        assert resp.status_code == 200


# ================================================================
# GET /api/v1/auth/me
# ================================================================

class TestGetMe:
    async def test_me_returns_user_profile(self, test_client, test_user, auth_headers):
        resp = await test_client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert data["is_admin"] is False

    async def test_me_requires_auth(self, test_client, mock_db):
        resp = await test_client.get("/api/v1/auth/me")
        assert resp.status_code == 403  # HTTPBearer returns 403 if header missing

    async def test_me_invalid_token_returns_401_or_403(self, test_client, mock_db):
        resp = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code in (401, 403)

    async def test_me_does_not_expose_password(self, test_client, test_user, auth_headers):
        resp = await test_client.get("/api/v1/auth/me", headers=auth_headers)
        assert "hashed_password" not in resp.json()
        assert "password" not in resp.json()


# ================================================================
# POST /api/v1/auth/change-password
# ================================================================

class TestChangePassword:
    async def test_change_password_success(self, test_client, test_user, auth_headers):
        resp = await test_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password123!", "new_password": "NewPassword456!"},
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_change_password_wrong_current_returns_401(
        self, test_client, test_user, auth_headers
    ):
        resp = await test_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "WrongCurrent!", "new_password": "NewPassword456!"},
            headers=auth_headers,
        )
        assert resp.status_code == 401

    async def test_change_password_new_too_short_returns_422(
        self, test_client, test_user, auth_headers
    ):
        resp = await test_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password123!", "new_password": "short"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_change_password_requires_auth(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Password123!", "new_password": "NewPassword456!"},
        )
        assert resp.status_code == 403
