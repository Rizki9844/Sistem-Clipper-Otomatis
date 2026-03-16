"""
Integration Tests: Health & Root Endpoints
=============================================
Tests for GET /health and GET / (no auth required).
Also verifies global error handling responses.
"""

import pytest


# ================================================================
# GET /health
# ================================================================

class TestHealthCheck:
    async def test_health_returns_200(self, test_client, mock_db):
        resp = await test_client.get("/health")
        assert resp.status_code == 200

    async def test_health_response_structure(self, test_client, mock_db):
        resp = await test_client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "app" in data
        assert "version" in data
        assert "checks" in data

    async def test_health_no_auth_required(self, test_client, mock_db):
        """Health check must be publicly accessible."""
        resp = await test_client.get("/health")
        # Should not be 401 or 403
        assert resp.status_code != 401
        assert resp.status_code != 403

    async def test_health_app_name_correct(self, test_client, mock_db):
        from app.config import settings
        resp = await test_client.get("/health")
        assert resp.json()["app"] == settings.APP_NAME


# ================================================================
# GET /
# ================================================================

class TestRootEndpoint:
    async def test_root_returns_200(self, test_client, mock_db):
        resp = await test_client.get("/")
        assert resp.status_code == 200

    async def test_root_contains_quickstart_guide(self, test_client, mock_db):
        resp = await test_client.get("/")
        data = resp.json()
        assert "quickstart" in data
        assert "submit_url" in data["quickstart"]

    async def test_root_no_auth_required(self, test_client, mock_db):
        resp = await test_client.get("/")
        assert resp.status_code not in (401, 403)


# ================================================================
# Global exception handling
# ================================================================

class TestExceptionHandling:
    async def test_404_on_unknown_route(self, test_client, mock_db):
        resp = await test_client.get("/api/v1/nonexistent-route")
        assert resp.status_code == 404

    async def test_method_not_allowed(self, test_client, mock_db):
        # PUT is not defined on /health
        resp = await test_client.put("/health")
        assert resp.status_code == 405

    async def test_missing_auth_returns_403_not_500(self, test_client, mock_db):
        """Endpoints requiring auth should return 403, not 500."""
        resp = await test_client.get("/api/v1/videos/")
        assert resp.status_code == 403
