from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from calorie_app.adapters.db.models import MealEntryModel, RecipeModel, UserModel, WaterEntryModel
from calorie_app.core.domain import (
    MealEntry,
    NutritionFacts,
    RecipeEntry,
    User,
    UserSettings,
    WaterEntry,
)


def _user_from_model(m: UserModel) -> User:
    from calorie_app.core.domain import MacroTargets, MealReminderTimes, ReminderSettings

    raw = m.settings or {}
    macro_raw = raw.get("macro_targets", {})
    times_raw = raw.get("meal_times", {})
    rem_raw = raw.get("reminders", {})
    settings = UserSettings(
        calorie_target=raw.get("calorie_target", 2000),
        water_target_ml=raw.get("water_target_ml", 2000),
        macro_targets=MacroTargets(
            protein_g=macro_raw.get("protein_g", 120),
            fat_g=macro_raw.get("fat_g", 70),
            carbs_g=macro_raw.get("carbs_g", 250),
        ),
        meal_times=MealReminderTimes(
            breakfast=times_raw.get("breakfast", "08:00"),
            lunch=times_raw.get("lunch", "13:00"),
            dinner=times_raw.get("dinner", "19:00"),
        ),
        timezone=raw.get("timezone", "Europe/Moscow"),
        reminders=ReminderSettings(
            meal_enabled=rem_raw.get("meal_enabled", True),
            water_enabled=rem_raw.get("water_enabled", True),
            summary_enabled=rem_raw.get("summary_enabled", True),
        ),
        profile_text=raw.get("profile_text", ""),
        goal_description=raw.get("goal_description", ""),
        kitchen_equipment=raw.get("kitchen_equipment", []),
        food_preferences=raw.get("food_preferences", ""),
        body_data=raw.get("body_data", {}),
    )
    return User(
        telegram_id=m.telegram_id,
        username=m.username,
        first_name=m.first_name,
        settings=settings,
        created_at=m.created_at,
    )


def _meal_from_model(m: MealEntryModel) -> MealEntry:
    return MealEntry(
        id=m.id,
        user_id=m.user_id,
        description=m.description,
        photo_path=m.photo_path,
        nutrition=NutritionFacts(
            calories=m.calories or 0,
            protein_g=float(m.protein_g or 0),
            fat_g=float(m.fat_g or 0),
            carbs_g=float(m.carbs_g or 0),
            portion_g=m.portion_g or 0,
        ),
        confidence=m.confidence or "medium",  # type: ignore[arg-type]
        gemini_raw=m.gemini_raw or {},
        confirmed=m.confirmed,
        logged_at=m.logged_at,
        created_at=m.created_at,
    )


def _water_from_model(m: WaterEntryModel) -> WaterEntry:
    return WaterEntry(
        id=m.id,
        user_id=m.user_id,
        amount_ml=m.amount_ml,
        logged_at=m.logged_at,
    )


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def upsert(self, user: User) -> User:
        stmt = (
            pg_insert(UserModel)
            .values(
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=user.first_name,
                settings={},
            )
            .on_conflict_do_update(
                index_elements=["telegram_id"],
                set_={"username": user.username, "first_name": user.first_name},
            )
            .returning(UserModel)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        await self._session.commit()
        return _user_from_model(model)

    async def update_settings(self, telegram_id: int, settings_dict: dict) -> None:  # type: ignore[type-arg]
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.settings = {**(model.settings or {}), **settings_dict}
            await self._session.commit()


class MealRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, meal: MealEntry) -> MealEntry:
        model = MealEntryModel(
            id=meal.id,
            user_id=meal.user_id,
            logged_at=meal.logged_at,
            description=meal.description,
            photo_path=meal.photo_path,
            calories=meal.nutrition.calories,
            protein_g=meal.nutrition.protein_g,
            fat_g=meal.nutrition.fat_g,
            carbs_g=meal.nutrition.carbs_g,
            portion_g=meal.nutrition.portion_g,
            confidence=meal.confidence,
            gemini_raw=meal.gemini_raw,
            confirmed=meal.confirmed,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _meal_from_model(model)

    async def get_by_date(self, user_id: int, log_date: date) -> list[MealEntry]:
        start = datetime(log_date.year, log_date.month, log_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(log_date.year, log_date.month, log_date.day, 23, 59, 59, tzinfo=timezone.utc)
        result = await self._session.execute(
            select(MealEntryModel)
            .where(
                MealEntryModel.user_id == user_id,
                MealEntryModel.logged_at >= start,
                MealEntryModel.logged_at <= end,
                MealEntryModel.confirmed.is_(True),
            )
            .order_by(MealEntryModel.logged_at)
        )
        return [_meal_from_model(m) for m in result.scalars().all()]

    async def get_dates_with_logs(self, user_id: int, days: int = 30) -> list[str]:
        result = await self._session.execute(
            select(func.date(MealEntryModel.logged_at).label("log_date"))
            .where(MealEntryModel.user_id == user_id, MealEntryModel.confirmed.is_(True))
            .group_by(func.date(MealEntryModel.logged_at))
            .order_by(func.date(MealEntryModel.logged_at).desc())
            .limit(days)
        )
        return [str(row.log_date) for row in result.all()]

    async def get_history_summary(self, user_id: int, days: int = 90) -> list[dict]:  # type: ignore[type-arg]
        result = await self._session.execute(
            select(
                func.date(MealEntryModel.logged_at).label("log_date"),
                func.count(MealEntryModel.id).label("meal_count"),
                func.sum(MealEntryModel.calories).label("calories"),
            )
            .where(MealEntryModel.user_id == user_id, MealEntryModel.confirmed.is_(True))
            .group_by(func.date(MealEntryModel.logged_at))
            .order_by(func.date(MealEntryModel.logged_at).desc())
            .limit(days)
        )
        return [
            {
                "date": str(row.log_date),
                "meal_count": int(row.meal_count),
                "calories": int(row.calories or 0),
            }
            for row in result.all()
        ]

    async def update(
        self,
        meal_id: uuid.UUID,
        user_id: int,
        description: str | None = None,
        nutrition: NutritionFacts | None = None,
        confidence: str | None = None,
    ) -> MealEntry | None:
        result = await self._session.execute(
            select(MealEntryModel).where(
                MealEntryModel.id == meal_id,
                MealEntryModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        if description is not None:
            model.description = description
        if nutrition is not None:
            model.calories = nutrition.calories
            model.protein_g = nutrition.protein_g
            model.fat_g = nutrition.fat_g
            model.carbs_g = nutrition.carbs_g
            model.portion_g = nutrition.portion_g
        if confidence is not None:
            model.confidence = confidence  # type: ignore[assignment]
        await self._session.commit()
        await self._session.refresh(model)
        return _meal_from_model(model)

    async def delete(self, meal_id: uuid.UUID, user_id: int) -> bool:
        result = await self._session.execute(
            delete(MealEntryModel)
            .where(
                MealEntryModel.id == meal_id,
                MealEntryModel.user_id == user_id,
            )
            .returning(MealEntryModel.id)
        )
        await self._session.commit()
        return result.scalar_one_or_none() is not None

    async def get_weekly_summary(self, user_id: int) -> list[dict]:  # type: ignore[type-arg]
        result = await self._session.execute(
            select(
                func.date(MealEntryModel.logged_at).label("log_date"),
                func.sum(MealEntryModel.calories).label("calories"),
                func.sum(MealEntryModel.protein_g).label("protein_g"),
                func.sum(MealEntryModel.fat_g).label("fat_g"),
                func.sum(MealEntryModel.carbs_g).label("carbs_g"),
            )
            .where(MealEntryModel.user_id == user_id, MealEntryModel.confirmed.is_(True))
            .group_by(func.date(MealEntryModel.logged_at))
            .order_by(func.date(MealEntryModel.logged_at).desc())
            .limit(7)
        )
        return [
            {
                "date": str(row.log_date),
                "calories": int(row.calories or 0),
                "protein_g": float(row.protein_g or 0),
                "fat_g": float(row.fat_g or 0),
                "carbs_g": float(row.carbs_g or 0),
            }
            for row in result.all()
        ]


class WaterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entry: WaterEntry) -> WaterEntry:
        model = WaterEntryModel(
            id=entry.id,
            user_id=entry.user_id,
            logged_at=entry.logged_at,
            amount_ml=entry.amount_ml,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _water_from_model(model)

    async def get_by_date(self, user_id: int, log_date: date) -> list[WaterEntry]:
        start = datetime(log_date.year, log_date.month, log_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(log_date.year, log_date.month, log_date.day, 23, 59, 59, tzinfo=timezone.utc)
        result = await self._session.execute(
            select(WaterEntryModel)
            .where(
                WaterEntryModel.user_id == user_id,
                WaterEntryModel.logged_at >= start,
                WaterEntryModel.logged_at <= end,
            )
            .order_by(WaterEntryModel.logged_at)
        )
        return [_water_from_model(m) for m in result.scalars().all()]


def _recipe_from_model(m: RecipeModel) -> RecipeEntry:
    n = m.nutrition_estimate or {}
    return RecipeEntry(
        id=m.id,
        user_id=m.user_id,
        title=m.title,
        description=m.description or "",
        ingredients=m.ingredients or [],
        instructions=m.instructions or [],
        nutrition_estimate=NutritionFacts(
            calories=n.get("calories", 0),
            protein_g=float(n.get("protein_g", 0)),
            fat_g=float(n.get("fat_g", 0)),
            carbs_g=float(n.get("carbs_g", 0)),
            portion_g=n.get("portion_g", 0),
        ),
        cooking_time_min=m.cooking_time_min or 30,
        equipment_used=m.equipment_used or [],
        liked=m.liked,
        created_at=m.created_at,
    )


class RecipeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, recipe: RecipeEntry) -> RecipeEntry:
        model = RecipeModel(
            id=recipe.id,
            user_id=recipe.user_id,
            title=recipe.title,
            description=recipe.description,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            nutrition_estimate={
                "calories": recipe.nutrition_estimate.calories,
                "protein_g": recipe.nutrition_estimate.protein_g,
                "fat_g": recipe.nutrition_estimate.fat_g,
                "carbs_g": recipe.nutrition_estimate.carbs_g,
                "portion_g": recipe.nutrition_estimate.portion_g,
            },
            cooking_time_min=recipe.cooking_time_min,
            equipment_used=recipe.equipment_used,
            liked=recipe.liked,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _recipe_from_model(model)

    async def set_feedback(self, recipe_id: uuid.UUID, user_id: int, liked: bool) -> RecipeEntry | None:
        result = await self._session.execute(
            select(RecipeModel).where(
                RecipeModel.id == recipe_id,
                RecipeModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.liked = liked
        await self._session.commit()
        await self._session.refresh(model)
        return _recipe_from_model(model)

    async def get_history(self, user_id: int, limit: int = 50) -> list[RecipeEntry]:
        result = await self._session.execute(
            select(RecipeModel)
            .where(RecipeModel.user_id == user_id)
            .order_by(RecipeModel.created_at.desc())
            .limit(limit)
        )
        return [_recipe_from_model(m) for m in result.scalars().all()]

    async def get_liked_titles(self, user_id: int) -> list[str]:
        result = await self._session.execute(
            select(RecipeModel.title)
            .where(RecipeModel.user_id == user_id, RecipeModel.liked.is_(True))
            .order_by(RecipeModel.created_at.desc())
            .limit(10)
        )
        return [row[0] for row in result.all()]

    async def get_disliked_titles(self, user_id: int) -> list[str]:
        result = await self._session.execute(
            select(RecipeModel.title)
            .where(RecipeModel.user_id == user_id, RecipeModel.liked.is_(False))
            .order_by(RecipeModel.created_at.desc())
            .limit(10)
        )
        return [row[0] for row in result.all()]
