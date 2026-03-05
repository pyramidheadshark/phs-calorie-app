from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from calorie_app.api.deps import get_current_user
from calorie_app.adapters.db.session import get_session
from calorie_app.core.domain import MealEntry, NutritionFacts, User, UserSettings
from calorie_app.main import app


def _fake_user() -> User:
    return User(
        telegram_id=999888777,
        username="loguser",
        first_name="Log",
        settings=UserSettings(calorie_target=2000),
    )


@pytest.fixture()
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture()
def client_with_overrides(mock_db_session: AsyncMock) -> AsyncClient:
    async def override_user() -> User:
        return _fake_user()

    async def override_session():  # type: ignore[return]
        yield mock_db_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestGetHistory:
    async def test_returns_history_days(self, client_with_overrides: AsyncClient) -> None:
        summary = [
            {"date": "2026-03-04", "meal_count": 4, "calories": 2100},
            {"date": "2026-03-03", "meal_count": 3, "calories": 1750},
        ]
        with patch("calorie_app.api.logs.MealRepo") as MockRepo:
            MockRepo.return_value.get_history_summary = AsyncMock(return_value=summary)
            async with client_with_overrides as client:
                response = await client.get("/api/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["days"]) == 2
        assert data["days"][0]["date"] == "2026-03-04"
        assert data["days"][0]["meal_count"] == 4
        assert data["days"][1]["calories"] == 1750

    async def test_empty_history(self, client_with_overrides: AsyncClient) -> None:
        with patch("calorie_app.api.logs.MealRepo") as MockRepo:
            MockRepo.return_value.get_history_summary = AsyncMock(return_value=[])
            async with client_with_overrides as client:
                response = await client.get("/api/history")

        assert response.status_code == 200
        assert response.json()["days"] == []


class TestGetDailyLog:
    async def test_returns_meals_and_totals(self, client_with_overrides: AsyncClient) -> None:
        meal = MealEntry(
            user_id=999888777,
            description="Борщ",
            nutrition=NutritionFacts(calories=300, protein_g=12.0, fat_g=8.0, carbs_g=40.0, portion_g=400),
            confidence="high",
            confirmed=True,
            logged_at=datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc),
        )
        with patch("calorie_app.api.logs.MealRepo") as MockRepo:
            MockRepo.return_value.get_by_date = AsyncMock(return_value=[meal])
            async with client_with_overrides as client:
                response = await client.get("/api/daily/2026-03-04")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-03-04"
        assert len(data["meals"]) == 1
        assert data["meals"][0]["description"] == "Борщ"
        assert data["total_nutrition"]["calories"] == 300
        # no water fields
        assert "total_water_ml" not in data
        assert "water_entries" not in data

    async def test_empty_day_zero_totals(self, client_with_overrides: AsyncClient) -> None:
        with patch("calorie_app.api.logs.MealRepo") as MockRepo:
            MockRepo.return_value.get_by_date = AsyncMock(return_value=[])
            async with client_with_overrides as client:
                response = await client.get("/api/daily/2026-03-01")

        assert response.status_code == 200
        assert response.json()["total_nutrition"]["calories"] == 0


class TestAuthRequired:
    async def test_missing_header_blocked(self) -> None:
        original = app.dependency_overrides.copy()
        app.dependency_overrides.clear()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/history")
            assert response.status_code in (401, 422)
        finally:
            app.dependency_overrides.update(original)
