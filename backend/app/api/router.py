"""
Main API Router
=================
Aggregates all endpoint routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.endpoints import videos, clips, jobs, styles
from app.api.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(clips.router, prefix="/clips", tags=["Clips"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(styles.router, prefix="/styles", tags=["Caption Styles"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
