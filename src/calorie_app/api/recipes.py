from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from calorie_app.adapters.db.repos import RecipeRepo
from calorie_app.adapters.db.session import get_session
from calorie_app.adapters.gemini import gemini_adapter
from calorie_app.api.deps import get_current_user
from calorie_app.core.domain import RecipeEntry, User
from calorie_app.models.schemas import RecipeFeedbackRequest, RecipeResponse

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


def _recipe_to_schema(r: RecipeEntry) -> RecipeResponse:
    return RecipeResponse(
        id=r.id,
        title=r.title,
        description=r.description,
        ingredients=[{"name": i.get("name", ""), "amount": i.get("amount", "")} for i in r.ingredients],
        instructions=r.instructions,
        nutrition_estimate={
            "calories": r.nutrition_estimate.calories,
            "protein_g": r.nutrition_estimate.protein_g,
            "fat_g": r.nutrition_estimate.fat_g,
            "carbs_g": r.nutrition_estimate.carbs_g,
            "portion_g": r.nutrition_estimate.portion_g,
        },
        cooking_time_min=r.cooking_time_min,
        equipment_used=r.equipment_used,
        liked=r.liked,
        created_at=r.created_at,
    )


@router.post("/generate", response_model=RecipeResponse)
async def generate_recipe(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecipeResponse:
    s = current_user.settings
    repo = RecipeRepo(session)
    liked_titles = await repo.get_liked_titles(current_user.telegram_id)
    disliked_titles = await repo.get_disliked_titles(current_user.telegram_id)

    try:
        recipe = await gemini_adapter.generate_recipe(
            user_id=current_user.telegram_id,
            goal=s.goal_description,
            calorie_target=s.calorie_target,
            protein_g=s.macro_targets.protein_g,
            fat_g=s.macro_targets.fat_g,
            carbs_g=s.macro_targets.carbs_g,
            preferences=s.food_preferences,
            equipment=s.kitchen_equipment,
            liked_titles=liked_titles,
            disliked_titles=disliked_titles,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Recipe generation failed: {e}") from e

    saved = await repo.save(recipe)
    return _recipe_to_schema(saved)


@router.get("", response_model=list[RecipeResponse])
async def get_recipe_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[RecipeResponse]:
    repo = RecipeRepo(session)
    recipes = await repo.get_history(current_user.telegram_id)
    return [_recipe_to_schema(r) for r in recipes]


@router.patch("/{recipe_id}/feedback", response_model=RecipeResponse)
async def set_recipe_feedback(
    recipe_id: uuid.UUID,
    body: RecipeFeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecipeResponse:
    repo = RecipeRepo(session)
    recipe = await repo.set_feedback(recipe_id, current_user.telegram_id, body.liked)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_to_schema(recipe)
