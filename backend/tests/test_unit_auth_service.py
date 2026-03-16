"""
Unit Tests: Auth Service
==========================
Tests for password hashing (bcrypt) and JWT token creation/verification.
No database or HTTP layer — pure function tests.
"""

from datetime import datetime, timedelta

import pytest
from jose import jwt

from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.config import settings


# ------------------------------------------------------------------ Password hashing

class TestHashPassword:
    def test_returns_different_hash_each_call(self):
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        # bcrypt salts are random
        assert h1 != h2

    def test_hash_is_not_plaintext(self):
        h = hash_password("secret123")
        assert "secret123" not in h

    def test_hash_starts_with_bcrypt_prefix(self):
        h = hash_password("secret123")
        assert h.startswith("$2")


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_empty_password_fails(self):
        h = hash_password("realpassword")
        assert verify_password("", h) is False

    def test_case_sensitive(self):
        h = hash_password("Password")
        assert verify_password("password", h) is False
        assert verify_password("PASSWORD", h) is False


# ------------------------------------------------------------------ JWT tokens

FAKE_USER_ID = "507f1f77bcf86cd799439011"
FAKE_EMAIL = "test@example.com"


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token(FAKE_USER_ID, FAKE_EMAIL, is_admin=False)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_payload_contains_required_fields(self):
        token = create_access_token(FAKE_USER_ID, FAKE_EMAIL, is_admin=False)
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["sub"] == FAKE_USER_ID
        assert payload["email"] == FAKE_EMAIL
        assert payload["is_admin"] is False
        assert "exp" in payload

    def test_admin_flag_propagated(self):
        token = create_access_token(FAKE_USER_ID, FAKE_EMAIL, is_admin=True)
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["is_admin"] is True

    def test_expiry_is_in_the_future(self):
        token = create_access_token(FAKE_USER_ID, FAKE_EMAIL, is_admin=False)
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        exp = datetime.utcfromtimestamp(payload["exp"])
        assert exp > datetime.utcnow()


class TestDecodeAccessToken:
    def test_valid_token_returns_payload(self):
        token = create_access_token(FAKE_USER_ID, FAKE_EMAIL, is_admin=False)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == FAKE_USER_ID
        assert payload["email"] == FAKE_EMAIL

    def test_tampered_token_returns_none(self):
        token = create_access_token(FAKE_USER_ID, FAKE_EMAIL, is_admin=False)
        tampered = token[:-5] + "xxxxx"
        assert decode_access_token(tampered) is None

    def test_wrong_secret_returns_none(self):
        token = jwt.encode(
            {"sub": FAKE_USER_ID, "exp": datetime.utcnow() + timedelta(hours=1)},
            key="wrong-secret",
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_access_token(token) is None

    def test_expired_token_returns_none(self):
        expired_payload = {
            "sub": FAKE_USER_ID,
            "email": FAKE_EMAIL,
            "is_admin": False,
            "exp": datetime.utcnow() - timedelta(seconds=1),
        }
        token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_access_token(token) is None

    def test_garbage_string_returns_none(self):
        assert decode_access_token("not.a.token") is None

    def test_empty_string_returns_none(self):
        assert decode_access_token("") is None
