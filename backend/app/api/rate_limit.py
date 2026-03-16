"""
Rate Limiting
===============
SlowAPI-based rate limiting with Redis backend.
Key function: authenticated users → user_id, anonymous → IP address.

Usage in endpoints:
    from app.api.rate_limit import limiter

    @router.post("/endpoint")
    @limiter.limit("10/minute")
    async def my_endpoint(request: Request, ...):
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings


def _get_key(request: Request) -> str:
    """
    Rate limit key: extract user_id from JWT if present, fallback to IP.
    This avoids punishing all users behind the same IP (e.g. office NAT).
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.auth_service import decode_access_token
            payload = decode_access_token(auth[7:])
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_key,
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.REDIS_URL if settings.is_production else None,
    strategy="fixed-window",
)
