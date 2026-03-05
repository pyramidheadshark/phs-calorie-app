from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from calorie_app.adapters.db.repos import MealRepo
from calorie_app.adapters.db.session import get_session
from calorie_app.api.deps import get_current_user
from calorie_app.core.domain import DailyLog, User
from calorie_app.core.calculator import compute_streak
from calorie_app.models.schemas import (
    DailyLogResponse,
    HistoryDaySchema,
    HistoryResponse,
    MealResponse,
    NutritionFactsSchema,
    StreakResponse,
    WeeklyDaySummary,
    WeeklyStatsResponse,
)

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/daily/{log_date}", response_model=DailyLogResponse)
async def get_daily_log(
    log_date: date,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DailyLogResponse:
    meal_repo = MealRepo(session)
    meals = await meal_repo.get_by_date(current_user.telegram_id, log_date)

    log = DailyLog(
        user_id=current_user.telegram_id,
        date=str(log_date),
        meals=meals,
    )
    total = log.total_nutrition

    return DailyLogResponse(
        date=str(log_date),
        meals=[
            MealResponse(
                id=m.id,
                description=m.description,
                nutrition=NutritionFactsSchema(
                    calories=m.nutrition.calories,
                    protein_g=m.nutrition.protein_g,
                    fat_g=m.nutrition.fat_g,
                    carbs_g=m.nutrition.carbs_g,
                    portion_g=m.nutrition.portion_g,
                ),
                confidence=m.confidence,
                photo_path=m.photo_path,
                logged_at=m.logged_at,
                confirmed=m.confirmed,
            )
            for m in meals
        ],
        total_nutrition=NutritionFactsSchema(
            calories=total.calories,
            protein_g=total.protein_g,
            fat_g=total.fat_g,
            carbs_g=total.carbs_g,
            portion_g=total.portion_g,
        ),
    )


@router.get("/stats/weekly", response_model=WeeklyStatsResponse)
async def get_weekly_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WeeklyStatsResponse:
    repo = MealRepo(session)
    summary = await repo.get_weekly_summary(current_user.telegram_id)
    return WeeklyStatsResponse(
        days=[
            WeeklyDaySummary(
                date=row["date"],
                calories=row["calories"],
                protein_g=row["protein_g"],
                fat_g=row["fat_g"],
                carbs_g=row["carbs_g"],
            )
            for row in summary
        ]
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HistoryResponse:
    repo = MealRepo(session)
    summary = await repo.get_history_summary(current_user.telegram_id)
    return HistoryResponse(
        days=[
            HistoryDaySchema(
                date=row["date"],
                meal_count=row["meal_count"],
                calories=row["calories"],
            )
            for row in summary
        ]
    )


@router.get("/stats/streak", response_model=StreakResponse)
async def get_streak(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreakResponse:
    repo = MealRepo(session)
    dates = await repo.get_dates_with_logs(current_user.telegram_id)
    return StreakResponse(streak_days=compute_streak(dates))
