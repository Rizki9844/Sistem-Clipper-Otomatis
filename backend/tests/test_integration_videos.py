"""
Integration Tests: Videos Endpoints
======================================
Tests for GET /videos/, GET /videos/{id}, DELETE /videos/{id}.

Note: POST /from-url and POST /upload are NOT tested here because they
require yt-dlp (external network) and Azure Blob Storage — those are
covered by separate E2E/smoke tests.

Fixtures from conftest.py:
  - test_client, mock_db, test_user, auth_headers, sample_video
"""

import pytest
from unittest.mock import AsyncMock, patch


# ================================================================
# GET /api/v1/videos/
# ================================================================

class TestListVideos:
    async def test_list_returns_empty_for_new_user(self, test_client, auth_headers, mock_db):
        resp = await test_client.get("/api/v1/videos/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_returns_own_videos(self, test_client, auth_headers, sample_video):
        resp = await test_client.get("/api/v1/videos/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(sample_video.id)

    async def test_list_requires_auth(self, test_client, mock_db):
        resp = await test_client.get("/api/v1/videos/")
        assert resp.status_code == 403

    async def test_list_filters_by_status(self, test_client, auth_headers, sample_video):
        resp = await test_client.get(
            "/api/v1/videos/", headers=auth_headers, params={"status": "downloaded"}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp2 = await test_client.get(
            "/api/v1/videos/", headers=auth_headers, params={"status": "completed"}
        )
        assert resp2.json() == []

    async def test_list_filters_by_source_type(self, test_client, auth_headers, sample_video):
        resp = await test_client.get(
            "/api/v1/videos/", headers=auth_headers, params={"source_type": "url"}
        )
        assert len(resp.json()) == 1

        resp2 = await test_client.get(
            "/api/v1/videos/", headers=auth_headers, params={"source_type": "upload"}
        )
        assert resp2.json() == []

    async def test_list_pagination(self, test_client, auth_headers, mock_db, test_user):
        from app.models.video import Video
        # Create 5 more videos
        for i in range(5):
            v = Video(
                original_filename=f"video_{i}.mp4",
                source_type="url",
                status="pending",
                user_id=str(test_user.id),
            )
            await v.insert()

        resp = await test_client.get(
            "/api/v1/videos/", headers=auth_headers, params={"limit": 3, "skip": 0}
        )
        assert len(resp.json()) == 3

        resp2 = await test_client.get(
            "/api/v1/videos/", headers=auth_headers, params={"limit": 3, "skip": 3}
        )
        assert len(resp2.json()) == 2

    async def test_list_does_not_return_other_users_videos(
        self, test_client, auth_headers, mock_db, admin_user
    ):
        """Videos owned by admin should not appear in test_user's list."""
        from app.models.video import Video
        other_video = Video(
            original_filename="other.mp4",
            source_type="upload",
            status="pending",
            user_id=str(admin_user.id),
        )
        await other_video.insert()

        resp = await test_client.get("/api/v1/videos/", headers=auth_headers)
        assert resp.json() == []


# ================================================================
# GET /api/v1/videos/{video_id}
# ================================================================

class TestGetVideo:
    async def test_get_own_video_success(self, test_client, auth_headers, sample_video):
        resp = await test_client.get(
            f"/api/v1/videos/{sample_video.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(sample_video.id)
        assert data["source_platform"] == "youtube"

    async def test_get_nonexistent_video_returns_404(self, test_client, auth_headers, mock_db):
        resp = await test_client.get(
            "/api/v1/videos/000000000000000000000001", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_other_users_video_returns_404(
        self, test_client, auth_headers, mock_db, admin_user
    ):
        """Should return 404 (not 403) to avoid info leakage."""
        from app.models.video import Video
        other_video = Video(
            original_filename="other.mp4",
            source_type="upload",
            status="pending",
            user_id=str(admin_user.id),
        )
        await other_video.insert()
        resp = await test_client.get(
            f"/api/v1/videos/{other_video.id}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_video_requires_auth(self, test_client, sample_video):
        resp = await test_client.get(f"/api/v1/videos/{sample_video.id}")
        assert resp.status_code == 403

    async def test_get_video_response_fields(self, test_client, auth_headers, sample_video):
        resp = await test_client.get(
            f"/api/v1/videos/{sample_video.id}", headers=auth_headers
        )
        data = resp.json()
        expected_fields = {
            "id", "filename", "original_filename", "file_size_bytes",
            "source_type", "status", "created_at",
        }
        assert expected_fields.issubset(data.keys())


# ================================================================
# DELETE /api/v1/videos/{video_id}
# ================================================================

class TestDeleteVideo:
    async def test_delete_own_video_success(self, test_client, auth_headers, sample_video):
        with patch(
            "app.services.storage.AzureBlobStorage.delete_blob",
            new=AsyncMock(return_value=None),
        ):
            resp = await test_client.delete(
                f"/api/v1/videos/{sample_video.id}", headers=auth_headers
            )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    async def test_delete_removes_video_from_db(self, test_client, auth_headers, sample_video):
        from app.models.video import Video
        with patch(
            "app.services.storage.AzureBlobStorage.delete_blob",
            new=AsyncMock(return_value=None),
        ):
            await test_client.delete(
                f"/api/v1/videos/{sample_video.id}", headers=auth_headers
            )
        remaining = await Video.get(sample_video.id)
        assert remaining is None

    async def test_delete_nonexistent_returns_404(self, test_client, auth_headers, mock_db):
        resp = await test_client.delete(
            "/api/v1/videos/000000000000000000000001", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_delete_other_users_video_returns_404(
        self, test_client, auth_headers, mock_db, admin_user
    ):
        from app.models.video import Video
        other_video = Video(
            original_filename="other.mp4",
            source_type="upload",
            status="pending",
            user_id=str(admin_user.id),
        )
        await other_video.insert()
        resp = await test_client.delete(
            f"/api/v1/videos/{other_video.id}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_delete_requires_auth(self, test_client, sample_video):
        resp = await test_client.delete(f"/api/v1/videos/{sample_video.id}")
        assert resp.status_code == 403
