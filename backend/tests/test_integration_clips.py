"""
Integration Tests: Clips Endpoints
=====================================
Tests for GET /clips/, GET /clips/{id}, POST /clips/{id}/review,
POST /clips/batch-review.

Fixtures from conftest.py:
  - test_client, mock_db, test_user, auth_headers
  - sample_video, sample_job, sample_clip
"""

import pytest
from unittest.mock import AsyncMock, patch


# ================================================================
# GET /api/v1/clips/
# ================================================================

class TestListClips:
    async def test_list_empty_for_new_user(self, test_client, auth_headers, mock_db):
        resp = await test_client.get("/api/v1/clips/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_returns_own_clips(self, test_client, auth_headers, sample_clip):
        resp = await test_client.get("/api/v1/clips/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(sample_clip.id)

    async def test_list_requires_auth(self, test_client, mock_db):
        resp = await test_client.get("/api/v1/clips/")
        assert resp.status_code == 403

    async def test_list_filters_by_video_id(self, test_client, auth_headers, sample_clip):
        resp = await test_client.get(
            "/api/v1/clips/",
            headers=auth_headers,
            params={"video_id": sample_clip.video_id},
        )
        assert len(resp.json()) == 1

        resp2 = await test_client.get(
            "/api/v1/clips/",
            headers=auth_headers,
            params={"video_id": "000000000000000000000001"},
        )
        assert resp2.json() == []

    async def test_list_filters_by_review_status(self, test_client, auth_headers, sample_clip):
        resp_pending = await test_client.get(
            "/api/v1/clips/",
            headers=auth_headers,
            params={"review_status": "pending"},
        )
        assert len(resp_pending.json()) == 1

        resp_approved = await test_client.get(
            "/api/v1/clips/",
            headers=auth_headers,
            params={"review_status": "approved"},
        )
        assert resp_approved.json() == []

    async def test_list_does_not_return_other_users_clips(
        self, test_client, auth_headers, mock_db, admin_user, sample_video, sample_job
    ):
        from app.models.clip import Clip
        other_clip = Clip(
            video_id=str(sample_video.id),
            job_id=str(sample_job.id),
            user_id=str(admin_user.id),
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            status="completed",
        )
        await other_clip.insert()
        resp = await test_client.get("/api/v1/clips/", headers=auth_headers)
        assert resp.json() == []

    async def test_list_clips_response_has_expected_fields(
        self, test_client, auth_headers, sample_clip
    ):
        resp = await test_client.get("/api/v1/clips/", headers=auth_headers)
        clip_data = resp.json()[0]
        expected = {"id", "video_id", "job_id", "start_time", "end_time",
                    "duration", "highlight_score", "status", "review_status", "created_at"}
        assert expected.issubset(clip_data.keys())


# ================================================================
# GET /api/v1/clips/{clip_id}
# ================================================================

class TestGetClip:
    async def test_get_own_clip_success(self, test_client, auth_headers, sample_clip):
        with patch(
            "app.services.storage.AzureBlobStorage.generate_sas_url",
            new=AsyncMock(return_value="https://example.com/sas"),
        ):
            resp = await test_client.get(
                f"/api/v1/clips/{sample_clip.id}", headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(sample_clip.id)

    async def test_get_nonexistent_clip_returns_404(self, test_client, auth_headers, mock_db):
        resp = await test_client.get(
            "/api/v1/clips/000000000000000000000001", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_other_users_clip_returns_404(
        self, test_client, auth_headers, mock_db, admin_user, sample_video, sample_job
    ):
        from app.models.clip import Clip
        other_clip = Clip(
            video_id=str(sample_video.id),
            job_id=str(sample_job.id),
            user_id=str(admin_user.id),
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            status="completed",
        )
        await other_clip.insert()
        resp = await test_client.get(
            f"/api/v1/clips/{other_clip.id}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_clip_requires_auth(self, test_client, sample_clip):
        resp = await test_client.get(f"/api/v1/clips/{sample_clip.id}")
        assert resp.status_code == 403


# ================================================================
# POST /api/v1/clips/{clip_id}/review
# ================================================================

class TestReviewClip:
    async def test_approve_clip(self, test_client, auth_headers, sample_clip):
        resp = await test_client.post(
            f"/api/v1/clips/{sample_clip.id}/review",
            headers=auth_headers,
            params={"action": "approve"},
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "approved"

        # Verify DB updated
        from app.models.clip import Clip
        updated = await Clip.get(sample_clip.id)
        assert updated.review_status == "approved"
        assert updated.reviewed_at is not None

    async def test_reject_clip(self, test_client, auth_headers, sample_clip):
        resp = await test_client.post(
            f"/api/v1/clips/{sample_clip.id}/review",
            headers=auth_headers,
            params={"action": "reject", "notes": "Low quality"},
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "rejected"

        from app.models.clip import Clip
        updated = await Clip.get(sample_clip.id)
        assert updated.review_notes == "Low quality"

    async def test_invalid_action_returns_400(self, test_client, auth_headers, sample_clip):
        resp = await test_client.post(
            f"/api/v1/clips/{sample_clip.id}/review",
            headers=auth_headers,
            params={"action": "delete"},
        )
        assert resp.status_code == 400

    async def test_review_other_users_clip_returns_404(
        self, test_client, auth_headers, mock_db, admin_user, sample_video, sample_job
    ):
        from app.models.clip import Clip
        other_clip = Clip(
            video_id=str(sample_video.id),
            job_id=str(sample_job.id),
            user_id=str(admin_user.id),
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            status="completed",
        )
        await other_clip.insert()
        resp = await test_client.post(
            f"/api/v1/clips/{other_clip.id}/review",
            headers=auth_headers,
            params={"action": "approve"},
        )
        assert resp.status_code == 404

    async def test_review_requires_auth(self, test_client, sample_clip):
        resp = await test_client.post(
            f"/api/v1/clips/{sample_clip.id}/review", params={"action": "approve"}
        )
        assert resp.status_code == 403


# ================================================================
# POST /api/v1/clips/batch-review
# ================================================================

class TestBatchReview:
    async def test_batch_approve_multiple_clips(
        self, test_client, auth_headers, mock_db, test_user, sample_video, sample_job
    ):
        from app.models.clip import Clip
        clips = []
        for i in range(3):
            c = Clip(
                video_id=str(sample_video.id),
                job_id=str(sample_job.id),
                user_id=str(test_user.id),
                start_time=float(i * 30),
                end_time=float(i * 30 + 30),
                duration=30.0,
                status="completed",
            )
            await c.insert()
            clips.append(c)

        clip_ids = [str(c.id) for c in clips]
        resp = await test_client.post(
            "/api/v1/clips/batch-review",
            headers=auth_headers,
            params={"action": "approve"},
            json=clip_ids,
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 3

    async def test_batch_review_skips_other_users_clips(
        self, test_client, auth_headers, mock_db, test_user, admin_user,
        sample_video, sample_job
    ):
        from app.models.clip import Clip
        own_clip = Clip(
            video_id=str(sample_video.id),
            job_id=str(sample_job.id),
            user_id=str(test_user.id),
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            status="completed",
        )
        await own_clip.insert()

        other_clip = Clip(
            video_id=str(sample_video.id),
            job_id=str(sample_job.id),
            user_id=str(admin_user.id),
            start_time=30.0,
            end_time=60.0,
            duration=30.0,
            status="completed",
        )
        await other_clip.insert()

        resp = await test_client.post(
            "/api/v1/clips/batch-review",
            headers=auth_headers,
            params={"action": "approve"},
            json=[str(own_clip.id), str(other_clip.id)],
        )
        assert resp.status_code == 200
        # Only the owned clip should be updated
        assert resp.json()["updated"] == 1

    async def test_batch_review_invalid_action_returns_400(
        self, test_client, auth_headers, mock_db
    ):
        resp = await test_client.post(
            "/api/v1/clips/batch-review",
            headers=auth_headers,
            params={"action": "invalid"},
            json=[],
        )
        assert resp.status_code == 400

    async def test_batch_review_requires_auth(self, test_client, mock_db):
        resp = await test_client.post(
            "/api/v1/clips/batch-review",
            params={"action": "approve"},
            json=[],
        )
        assert resp.status_code == 403
