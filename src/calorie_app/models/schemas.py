from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NutritionFactsSchema(BaseModel):
    calories: int = 0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    portion_g: int = 0


class MealAnalysisResponse(BaseModel):
    description: str
    nutrition: NutritionFactsSchema
    confidence: Literal["high", "medium", "low"]
    notes: str = ""


class MealConfirmRequest(BaseModel):
    description: str
    nutrition: NutritionFactsSchema
    confidence: Literal["high", "medium", "low"] = "high"
    photo_path: str | None = None
    gemini_raw: dict = Field(default_factory=dict)  # type: ignore[type-arg]


class MealResponse(BaseModel):
    id: uuid.UUID
    description: str
    nutrition: NutritionFactsSchema
    confidence: str
    photo_path: str | None
    logged_at: datetime
    confirmed: bool


class WaterLogRequest(BaseModel):
    amount_ml: int = Field(ge=50, le=2000)


class WaterEntryResponse(BaseModel):
    id: uuid.UUID
    amount_ml: int
    logged_at: datetime


class DailyLogResponse(BaseModel):
    date: str
    meals: list[MealResponse]
    water_entries: list[WaterEntryResponse]
    total_nutrition: NutritionFactsSchema
    total_water_ml: int


class WeeklyDaySummary(BaseModel):
    date: str
    calories: int
    protein_g: float
    fat_g: float
    carbs_g: float


class WeeklyStatsResponse(BaseModel):
    days: list[WeeklyDaySummary]


class StreakResponse(BaseModel):
    streak_days: int


class UserSettingsSchema(BaseModel):
    calorie_target: int = 2000
    water_target_ml: int = 2000
    protein_target_g: int = 120
    fat_target_g: int = 70
    carbs_target_g: int = 250
    breakfast_time: str = "08:00"
    lunch_time: str = "13:00"
    dinner_time: str = "19:00"
    timezone: str = "Europe/Moscow"
    meal_reminders_enabled: bool = True
    water_reminders_enabled: bool = True
    summary_enabled: bool = True
    profile_text: str = ""
    goal_description: str = ""
    kitchen_equipment: list[str] = Field(default_factory=list)
    food_preferences: str = ""
    body_data: dict = Field(default_factory=dict)  # type: ignore[type-arg]


class ProfileParseRequest(BaseModel):
    profile_text: str


class ProfileParseResponse(BaseModel):
    calorie_target: int
    protein_target_g: int
    fat_target_g: int
    carbs_target_g: int
    water_target_ml: int
    goal_description: str
    kitchen_equipment: list[str]
    food_preferences: str
    body_data: dict = Field(default_factory=dict)  # type: ignore[type-arg]


class IngredientSchema(BaseModel):
    name: str
    amount: str


class RecipeNutritionSchema(BaseModel):
    calories: int = 0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    portion_g: int = 0


class RecipeResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    ingredients: list[IngredientSchema]
    instructions: list[str]
    nutrition_estimate: RecipeNutritionSchema
    cooking_time_min: int
    equipment_used: list[str]
    liked: bool | None
    created_at: datetime


class RecipeFeedbackRequest(BaseModel):
    liked: bool


class MealUpdateRequest(BaseModel):
    description: str | None = None
    nutrition: NutritionFactsSchema | None = None
    confidence: Literal["high", "medium", "low"] | None = None


class MealTextRequest(BaseModel):
    description: str


class HistoryDaySchema(BaseModel):
    date: str
    meal_count: int
    calories: int


class HistoryResponse(BaseModel):
    days: list[HistoryDaySchema]
