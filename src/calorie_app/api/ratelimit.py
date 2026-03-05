from __future__ import annotations

import logging
from functools import lru_cache

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status

from calorie_app.api.deps import get_current_user
from calorie_app.config import settings
from calorie_app.core.domain import User

logger = logging.getLogger(__name__)

AI_REQUESTS_PER_HOUR = 30
AI_WINDOW_SECONDS = 3600


@lru_cache(maxsize=1)
def _get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def check_ai_rate_limit(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: enforces 30 AI requests / hour per user. Returns the user unchanged."""
    redis = _get_redis()
    key = f"rate:ai:{current_user.telegram_id}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, AI_WINDOW_SECONDS)
        if count > AI_REQUESTS_PER_HOUR:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"AI rate limit exceeded. Try again in {ttl}s.",
                headers={"Retry-After": str(ttl)},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis unavailable — log and allow the request through
        logger.warning("Rate limit check failed (Redis error): %s", exc)
    return current_user
