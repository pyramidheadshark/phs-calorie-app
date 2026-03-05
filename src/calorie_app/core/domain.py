from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class NutritionFacts:
    calories: int = 0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    portion_g: int = 0

    def __add__(self, other: NutritionFacts) -> NutritionFacts:
        return NutritionFacts(
            calories=self.calories + other.calories,
            protein_g=round(self.protein_g + other.protein_g, 1),
            fat_g=round(self.fat_g + other.fat_g, 1),
            carbs_g=round(self.carbs_g + other.carbs_g, 1),
            portion_g=self.portion_g + other.portion_g,
        )


@dataclass
class MealReminderTimes:
    breakfast: str = "08:00"
    lunch: str = "13:00"
    dinner: str = "19:00"


@dataclass
class MacroTargets:
    protein_g: int = 120
    fat_g: int = 70
    carbs_g: int = 250


@dataclass
class ReminderSettings:
    meal_enabled: bool = True
    summary_enabled: bool = True


@dataclass
class UserSettings:
    calorie_target: int = 2000
    macro_targets: MacroTargets = field(default_factory=MacroTargets)
    meal_times: MealReminderTimes = field(default_factory=MealReminderTimes)
    timezone: str = "Europe/Moscow"
    reminders: ReminderSettings = field(default_factory=ReminderSettings)
    profile_text: str = ""
    goal_description: str = ""
    kitchen_equipment: list[str] = field(default_factory=list)
    food_preferences: str = ""
    body_data: dict = field(default_factory=dict)  # type: ignore[type-arg]


@dataclass
class User:
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    settings: UserSettings = field(default_factory=UserSettings)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


Confidence = Literal["high", "medium", "low"]


@dataclass
class NutritionAnalysis:
    description: str
    nutrition: NutritionFacts
    confidence: Confidence
    notes: str = ""
    gemini_raw: dict = field(default_factory=dict)  # type: ignore[type-arg]


@dataclass
class MealEntry:
    user_id: int
    description: str
    nutrition: NutritionFacts
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    photo_path: str | None = None
    confidence: Confidence = "high"
    gemini_raw: dict = field(default_factory=dict)  # type: ignore[type-arg]
    confirmed: bool = True
    logged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RecipeEntry:
    user_id: int
    title: str
    description: str
    ingredients: list[dict]  # type: ignore[type-arg]
    instructions: list[str]
    nutrition_estimate: NutritionFacts
    cooking_time_min: int
    equipment_used: list[str]
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    liked: bool | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DailyLog:
    user_id: int
    date: str
    meals: list[MealEntry] = field(default_factory=list)

    @property
    def total_nutrition(self) -> NutritionFacts:
        result = NutritionFacts()
        for meal in self.meals:
            result = result + meal.nutrition
        return result
