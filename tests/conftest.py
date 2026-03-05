from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from calorie_app.core.domain import NutritionAnalysis, NutritionFacts, User, UserSettings


@pytest.fixture()
def fake_user() -> User:
    return User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        settings=UserSettings(calorie_target=2000),
    )


@pytest.fixture()
def fake_analysis() -> NutritionAnalysis:
    return NutritionAnalysis(
        description="Овсянка с бананом",
        nutrition=NutritionFacts(
            calories=350,
            protein_g=12.0,
            fat_g=8.0,
            carbs_g=60.0,
            portion_g=300,
        ),
        confidence="high",
        notes="Стандартная порция",
        gemini_raw={
            "description": "Овсянка с бананом",
            "calories": 350,
            "protein_g": 12.0,
            "fat_g": 8.0,
            "carbs_g": 60.0,
            "portion_g": 300,
            "confidence": "high",
            "notes": "Стандартная порция",
        },
    )


@pytest.fixture()
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session
