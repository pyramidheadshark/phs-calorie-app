from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from calorie_app.api.ratelimit import AI_REQUESTS_PER_HOUR, check_ai_rate_limit
from calorie_app.core.domain import User, UserSettings


def _make_user(telegram_id: int = 42) -> User:
    return User(telegram_id=telegram_id, settings=UserSettings())


class TestCheckAiRateLimit:
    async def test_allows_request_under_limit(self) -> None:
        user = _make_user()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=3500)

        with patch("calorie_app.api.ratelimit._get_redis", return_value=mock_redis):
            result = await check_ai_rate_limit(current_user=user)

        assert result is user
        mock_redis.incr.assert_called_once_with(f"rate:ai:{user.telegram_id}")
        mock_redis.expire.assert_called_once()

    async def test_does_not_reset_expiry_after_first_call(self) -> None:
        user = _make_user()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=5)  # not 1, already incremented before
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=3000)

        with patch("calorie_app.api.ratelimit._get_redis", return_value=mock_redis):
            await check_ai_rate_limit(current_user=user)

        mock_redis.expire.assert_not_called()

    async def test_blocks_request_over_limit(self) -> None:
        user = _make_user()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=AI_REQUESTS_PER_HOUR + 1)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=1800)

        with patch("calorie_app.api.ratelimit._get_redis", return_value=mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await check_ai_rate_limit(current_user=user)

        assert exc_info.value.status_code == 429
        assert "1800" in exc_info.value.detail

    async def test_allows_through_when_redis_unavailable(self) -> None:
        """If Redis is down, requests should still go through (fail-open)."""
        user = _make_user()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch("calorie_app.api.ratelimit._get_redis", return_value=mock_redis):
            result = await check_ai_rate_limit(current_user=user)

        assert result is user

    async def test_rate_limit_key_per_user(self) -> None:
        user_a = _make_user(telegram_id=100)
        user_b = _make_user(telegram_id=200)

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        captured_keys: list[str] = []

        async def capture_incr(key: str) -> int:
            captured_keys.append(key)
            return 1

        mock_redis.incr = capture_incr

        with patch("calorie_app.api.ratelimit._get_redis", return_value=mock_redis):
            await check_ai_rate_limit(current_user=user_a)
            await check_ai_rate_limit(current_user=user_b)

        assert captured_keys[0] == "rate:ai:100"
        assert captured_keys[1] == "rate:ai:200"
