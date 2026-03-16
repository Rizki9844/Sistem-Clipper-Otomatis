"""
WebSocket Endpoint
====================
Real-time job progress updates via WebSocket.
Clients connect with a job_id to receive live progress events.
"""

import json
import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.auth_service import decode_access_token
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("websocket")


class ConnectionManager:
    """Manages active WebSocket connections per job."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self._connections:
            self._connections[job_id] = []
        self._connections[job_id].append(websocket)
        logger.debug("WebSocket connected", job_id=job_id)

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self._connections:
            self._connections[job_id] = [
                ws for ws in self._connections[job_id] if ws != websocket
            ]
            if not self._connections[job_id]:
                del self._connections[job_id]
        logger.debug("WebSocket disconnected", job_id=job_id)

    async def send_to_job(self, job_id: str, data: dict):
        """Send a message to all clients watching a specific job."""
        if job_id not in self._connections:
            return

        dead = []
        for ws in self._connections[job_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            self._connections[job_id] = [
                w for w in self._connections[job_id] if w != ws
            ]

    async def broadcast(self, data: dict):
        """Send to all connected clients."""
        for job_id in list(self._connections.keys()):
            await self.send_to_job(job_id, data)


# Global connection manager
manager = ConnectionManager()


async def broadcast_job_update(
    job_id: str,
    status: str,
    step: str,
    progress: float,
    metadata: dict | None = None,
):
    """
    Called by worker tasks to push real-time updates.

    Usage (from any worker task):
        from app.api.websocket import broadcast_job_update
        await broadcast_job_update(job_id, "processing", "transcribe", 45.0)
    """
    await manager.send_to_job(job_id, {
        "type": "progress",
        "job_id": job_id,
        "status": status,
        "step": step,
        "progress": round(progress, 1),
        "metadata": metadata or {},
    })


@router.websocket("/ws/progress")
async def websocket_progress(
    websocket: WebSocket,
    job_id: Optional[str] = None,
    token: Optional[str] = None,
):
    """
    WebSocket endpoint for real-time job progress.
    Connect: ws://host/api/v1/ws/progress?job_id=xxx&token=<jwt>
    """
    if not job_id:
        await websocket.close(code=4001, reason="job_id query parameter required")
        return

    if not token:
        await websocket.close(code=4003, reason="token query parameter required")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    user_id = payload.get("sub")

    # Verify the job belongs to this user
    from app.models.job import Job
    job = await Job.get(job_id)
    if not job or job.user_id != user_id:
        await websocket.close(code=4004, reason="Job not found")
        return

    await manager.connect(websocket, job_id)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "initial",
            "job_id": job_id,
            "status": job.status,
            "step": job.current_step,
            "progress": job.overall_progress,
            "steps": job.steps,
        })

        # Keep connection alive — receive pings, send heartbeats
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception:
        manager.disconnect(websocket, job_id)
