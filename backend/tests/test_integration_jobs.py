"""
Integration Tests: Jobs Endpoints
=====================================
Tests for GET /jobs/, GET /jobs/{id}, POST /jobs/{id}/cancel,
POST /jobs/{id}/retry, GET /jobs/stats/dashboard.

Fixtures from conftest.py:
  - test_client, mock_db, test_user, auth_headers, sample_video, sample_job
"""

import pytest
from unittest.mock import patch


# ================================================================
# GET /api/v1/jobs/stats/dashboard
# ================================================================

class TestDashboardStats:
    async def test_dashboard_returns_zeroes_for_empty_user(
        self, test_client, auth_headers, mock_db
    ):
        resp = await test_client.get("/api/v1/jobs/stats/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_videos"] == 0
        assert data["total_jobs"] == 0
        assert data["total_clips"] == 0

    async def test_dashboard_counts_own_resources(
        self, test_client, auth_headers, sample_job
    ):
        resp = await test_client.get("/api/v1/jobs/stats/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_videos"] == 1
        assert data["total_jobs"] == 1

    async def test_dashboard_required_fields_present(
        self, test_client, auth_headers, mock_db
    ):
        resp = await test_client.get("/api/v1/jobs/stats/dashboard", headers=auth_headers)
        expected = {
            "total_videos", "total_jobs", "total_clips",
            "jobs_processing", "jobs_completed", "jobs_failed",
            "avg_processing_time_minutes", "clips_approved", "clips_rejected",
        }
        assert expected.issubset(resp.json().keys())

    async def test_dashboard_requires_auth(self, test_client, mock_db):
        resp = await test_client.get("/api/v1/jobs/stats/dashboard")
        assert resp.status_code == 403

    async def test_dashboard_does_not_count_other_users_jobs(
        self, test_client, auth_headers, mock_db, admin_user, sample_video
    ):
        from app.models.job import Job
        other_job = Job(
            video_id=str(sample_video.id),
            user_id=str(admin_user.id),
            status="completed",
        )
        await other_job.insert()

        resp = await test_client.get("/api/v1/jobs/stats/dashboard", headers=auth_headers)
        # sample_video is test_user's, but the extra job is admin_user's
        assert resp.json()["total_jobs"] == 0


# ================================================================
# GET /api/v1/jobs/
# ================================================================

class TestListJobs:
    async def test_list_empty_for_new_user(self, test_client, auth_headers, mock_db):
        resp = await test_client.get("/api/v1/jobs/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_returns_own_jobs(self, test_client, auth_headers, sample_job):
        resp = await test_client.get("/api/v1/jobs/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(sample_job.id)

    async def test_list_requires_auth(self, test_client, mock_db):
        resp = await test_client.get("/api/v1/jobs/")
        assert resp.status_code == 403

    async def test_list_filters_by_status(self, test_client, auth_headers, sample_job):
        resp = await test_client.get(
            "/api/v1/jobs/", headers=auth_headers, params={"status": "queued"}
        )
        assert len(resp.json()) == 1

        resp2 = await test_client.get(
            "/api/v1/jobs/", headers=auth_headers, params={"status": "completed"}
        )
        assert resp2.json() == []

    async def test_list_does_not_include_other_users_jobs(
        self, test_client, auth_headers, mock_db, admin_user, sample_video
    ):
        from app.models.job import Job
        other_job = Job(
            video_id=str(sample_video.id),
            user_id=str(admin_user.id),
            status="queued",
        )
        await other_job.insert()

        resp = await test_client.get("/api/v1/jobs/", headers=auth_headers)
        assert resp.json() == []


# ================================================================
# GET /api/v1/jobs/{job_id}
# ================================================================

class TestGetJob:
    async def test_get_own_job_success(self, test_client, auth_headers, sample_job):
        resp = await test_client.get(
            f"/api/v1/jobs/{sample_job.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(sample_job.id)
        assert data["status"] == "queued"

    async def test_get_nonexistent_job_returns_404(self, test_client, auth_headers, mock_db):
        resp = await test_client.get(
            "/api/v1/jobs/000000000000000000000001", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_other_users_job_returns_404(
        self, test_client, auth_headers, mock_db, admin_user, sample_video
    ):
        from app.models.job import Job
        other_job = Job(
            video_id=str(sample_video.id),
            user_id=str(admin_user.id),
        )
        await other_job.insert()
        resp = await test_client.get(
            f"/api/v1/jobs/{other_job.id}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_job_response_has_steps(self, test_client, auth_headers, sample_job):
        resp = await test_client.get(
            f"/api/v1/jobs/{sample_job.id}", headers=auth_headers
        )
        data = resp.json()
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) > 0

    async def test_get_job_requires_auth(self, test_client, sample_job):
        resp = await test_client.get(f"/api/v1/jobs/{sample_job.id}")
        assert resp.status_code == 403


# ================================================================
# POST /api/v1/jobs/{job_id}/cancel
# ================================================================

class TestCancelJob:
    async def test_cancel_queued_job_success(self, test_client, auth_headers, sample_job):
        resp = await test_client.post(
            f"/api/v1/jobs/{sample_job.id}/cancel", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["job_id"] == str(sample_job.id)

        # Verify status updated in DB
        from app.models.job import Job
        updated = await Job.get(sample_job.id)
        assert updated.status == "cancelled"

    async def test_cancel_completed_job_returns_400(
        self, test_client, auth_headers, sample_job
    ):
        sample_job.status = "completed"
        await sample_job.save()
        resp = await test_client.post(
            f"/api/v1/jobs/{sample_job.id}/cancel", headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_cancel_already_cancelled_returns_400(
        self, test_client, auth_headers, sample_job
    ):
        sample_job.status = "cancelled"
        await sample_job.save()
        resp = await test_client.post(
            f"/api/v1/jobs/{sample_job.id}/cancel", headers=auth_headers
        )
        assert resp.status_code == 400

    async def test_cancel_nonexistent_job_returns_404(
        self, test_client, auth_headers, mock_db
    ):
        resp = await test_client.post(
            "/api/v1/jobs/000000000000000000000001/cancel", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_cancel_requires_auth(self, test_client, sample_job):
        resp = await test_client.post(f"/api/v1/jobs/{sample_job.id}/cancel")
        assert resp.status_code == 403


# ================================================================
# POST /api/v1/jobs/{job_id}/retry
# ================================================================

class TestRetryJob:
    async def test_retry_non_failed_job_returns_400(
        self, test_client, auth_headers, sample_job
    ):
        # sample_job is "queued" — only "failed" jobs can be retried
        resp = await test_client.post(
            f"/api/v1/jobs/{sample_job.id}/retry", headers=auth_headers
        )
        assert resp.status_code == 400
        assert "failed" in resp.json()["detail"].lower()

    async def test_retry_failed_download_step(
        self, test_client, auth_headers, sample_job, sample_video
    ):
        # Mark job as failed at download step
        sample_job.status = "failed"
        for step in sample_job.steps:
            if step["name"] == "download":
                step["status"] = "failed"
                break
        await sample_job.save()

        # .delay() is synchronous in Celery — use regular MagicMock (default)
        with patch("app.workers.tasks.download.download_video") as mock_task:
            resp = await test_client.post(
                f"/api/v1/jobs/{sample_job.id}/retry", headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(sample_job.id)
        assert data["retry_count"] == 1

    async def test_retry_nonexistent_job_returns_404(
        self, test_client, auth_headers, mock_db
    ):
        resp = await test_client.post(
            "/api/v1/jobs/000000000000000000000001/retry", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_retry_requires_auth(self, test_client, sample_job):
        resp = await test_client.post(f"/api/v1/jobs/{sample_job.id}/retry")
        assert resp.status_code == 403
