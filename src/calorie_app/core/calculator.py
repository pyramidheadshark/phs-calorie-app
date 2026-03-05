from __future__ import annotations

from calorie_app.core.domain import DailyLog, NutritionFacts, UserSettings


def macro_percentages(nutrition: NutritionFacts) -> dict[str, float]:
    total_kcal = (
        nutrition.protein_g * 4 + nutrition.fat_g * 9 + nutrition.carbs_g * 4
    )
    if total_kcal == 0:
        return {"protein": 0.0, "fat": 0.0, "carbs": 0.0}
    return {
        "protein": round(nutrition.protein_g * 4 / total_kcal * 100, 1),
        "fat": round(nutrition.fat_g * 9 / total_kcal * 100, 1),
        "carbs": round(nutrition.carbs_g * 4 / total_kcal * 100, 1),
    }


def calorie_progress(log: DailyLog, settings: UserSettings) -> dict[str, int | float]:
    consumed = log.total_nutrition.calories
    target = settings.calorie_target
    remaining = max(0, target - consumed)
    return {
        "consumed": consumed,
        "target": target,
        "remaining": remaining,
        "percent": round(consumed / target * 100, 1) if target > 0 else 0.0,
    }


def compute_streak(logged_dates: list[str]) -> int:
    from datetime import date, timedelta

    if not logged_dates:
        return 0

    sorted_dates = sorted(set(logged_dates), reverse=True)
    streak = 0
    expected = date.today()
    for d in sorted_dates:
        current = date.fromisoformat(d)
        if current == expected or current == expected - timedelta(days=1) and streak == 0:
            streak += 1
            expected = current - timedelta(days=1)
        elif current == expected:
            streak += 1
            expected = current - timedelta(days=1)
        else:
            break
    return streak
