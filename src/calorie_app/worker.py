from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.schedules import crontab

from calorie_app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "calorie_app",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["calorie_app.worker"],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "cleanup-old-photos": {
        "task": "calorie_app.worker.cleanup_photos",
        "schedule": crontab(hour=3, minute=0),
    },
    "send-daily-summary": {
        "task": "calorie_app.worker.send_daily_summaries",
        "schedule": crontab(hour=21, minute=0),
    },
}


@celery_app.task(name="calorie_app.worker.cleanup_photos")
def cleanup_photos() -> int:
    from calorie_app.adapters.storage import photo_storage

    deleted = photo_storage.cleanup_old()
    logger.info("Cleaned up %d old photos", deleted)
    return deleted


@celery_app.task(name="calorie_app.worker.send_daily_summaries")
def send_daily_summaries() -> None:
    asyncio.run(_send_daily_summaries_async())


async def _send_daily_summaries_async() -> None:
    from datetime import date

    from calorie_app.adapters.db.repos import MealRepo
    from calorie_app.adapters.db.session import async_session_factory
    from calorie_app.adapters.db.models import UserModel
    from calorie_app.adapters.telegram import telegram_bot
    from calorie_app.core.domain import DailyLog
    from sqlalchemy import select

    today = date.today()

    async with async_session_factory() as session:
        result = await session.execute(select(UserModel))
        users = result.scalars().all()

        for user in users:
            settings_data = user.settings or {}
            reminders = settings_data.get("reminders", {})
            if not reminders.get("summary_enabled", True):
                continue

            meal_repo = MealRepo(session)
            meals = await meal_repo.get_by_date(user.telegram_id, today)

            if not meals:
                continue

            log = DailyLog(
                user_id=user.telegram_id,
                date=str(today),
                meals=meals,
            )
            total = log.total_nutrition
            calorie_target = settings_data.get("calorie_target", 2000)

            await telegram_bot.send_daily_summary(
                chat_id=user.telegram_id,
                calories=total.calories,
                target=calorie_target,
                protein_g=total.protein_g,
                fat_g=total.fat_g,
                carbs_g=total.carbs_g,
            )
