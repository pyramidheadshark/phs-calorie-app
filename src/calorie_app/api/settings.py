from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from calorie_app.adapters.db.repos import UserRepo
from calorie_app.adapters.db.session import get_session
from calorie_app.adapters.gemini import gemini_adapter
from calorie_app.api.deps import get_current_user
from calorie_app.core.domain import User
from calorie_app.models.schemas import ProfileParseRequest, ProfileParseResponse, UserSettingsSchema

router = APIRouter(prefix="/api/user", tags=["settings"])


def _settings_to_schema(s: object) -> UserSettingsSchema:
    from calorie_app.core.domain import UserSettings
    assert isinstance(s, UserSettings)
    return UserSettingsSchema(
        calorie_target=s.calorie_target,
        protein_target_g=s.macro_targets.protein_g,
        fat_target_g=s.macro_targets.fat_g,
        carbs_target_g=s.macro_targets.carbs_g,
        breakfast_time=s.meal_times.breakfast,
        lunch_time=s.meal_times.lunch,
        dinner_time=s.meal_times.dinner,
        timezone=s.timezone,
        meal_reminders_enabled=s.reminders.meal_enabled,
        summary_enabled=s.reminders.summary_enabled,
        profile_text=s.profile_text,
        goal_description=s.goal_description,
        kitchen_equipment=s.kitchen_equipment,
        food_preferences=s.food_preferences,
        body_data=s.body_data,
    )


@router.get("/settings", response_model=UserSettingsSchema)
async def get_settings(current_user: User = Depends(get_current_user)) -> UserSettingsSchema:
    return _settings_to_schema(current_user.settings)


@router.post("/settings", response_model=UserSettingsSchema)
async def update_settings(
    body: UserSettingsSchema,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserSettingsSchema:
    repo = UserRepo(session)
    settings_dict = {
        "calorie_target": body.calorie_target,
        "macro_targets": {
            "protein_g": body.protein_target_g,
            "fat_g": body.fat_target_g,
            "carbs_g": body.carbs_target_g,
        },
        "meal_times": {
            "breakfast": body.breakfast_time,
            "lunch": body.lunch_time,
            "dinner": body.dinner_time,
        },
        "timezone": body.timezone,
        "reminders": {
            "meal_enabled": body.meal_reminders_enabled,
            "summary_enabled": body.summary_enabled,
        },
        "profile_text": body.profile_text,
        "goal_description": body.goal_description,
        "kitchen_equipment": body.kitchen_equipment,
        "food_preferences": body.food_preferences,
        "body_data": body.body_data,
    }
    await repo.update_settings(current_user.telegram_id, settings_dict)
    return body


@router.post("/profile/parse", response_model=ProfileParseResponse)
async def parse_profile(
    body: ProfileParseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileParseResponse:
    try:
        parsed = await gemini_adapter.parse_profile(body.profile_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI parsing failed: {e}") from e

    repo = UserRepo(session)
    await repo.update_settings(
        current_user.telegram_id,
        {
            "calorie_target": parsed.get("calorie_target", 2000),
            "macro_targets": {
                "protein_g": parsed.get("protein_target_g", 120),
                "fat_g": parsed.get("fat_target_g", 70),
                "carbs_g": parsed.get("carbs_target_g", 250),
            },
            "profile_text": body.profile_text,
            "goal_description": parsed.get("goal_description", ""),
            "kitchen_equipment": parsed.get("kitchen_equipment", []),
            "food_preferences": parsed.get("food_preferences", ""),
            "body_data": parsed.get("body_data", {}),
        },
    )

    return ProfileParseResponse(
        calorie_target=parsed.get("calorie_target", 2000),
        protein_target_g=parsed.get("protein_target_g", 120),
        fat_target_g=parsed.get("fat_target_g", 70),
        carbs_target_g=parsed.get("carbs_target_g", 250),
        goal_description=parsed.get("goal_description", ""),
        kitchen_equipment=parsed.get("kitchen_equipment", []),
        food_preferences=parsed.get("food_preferences", ""),
        body_data=parsed.get("body_data", {}),
    )
