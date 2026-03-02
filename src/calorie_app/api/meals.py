from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from calorie_app.adapters.db.repos import MealRepo
from calorie_app.adapters.db.session import get_session
from calorie_app.adapters.gemini import gemini_adapter
from calorie_app.adapters.storage import photo_storage
from calorie_app.api.deps import get_current_user
from calorie_app.core.domain import MealEntry, NutritionFacts, User
from calorie_app.models.schemas import (
    MealAnalysisResponse,
    MealConfirmRequest,
    MealResponse,
    MealTextRequest,
    MealUpdateRequest,
    NutritionFactsSchema,
)

router = APIRouter(prefix="/api/meal", tags=["meals"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
ALLOWED_AUDIO_TYPES = {"audio/ogg", "audio/mpeg", "audio/wav", "audio/aac", "audio/flac"}
MAX_FILE_BYTES = 10 * 1024 * 1024


@router.post("/photo-path", response_model=MealAnalysisResponse)
async def analyze_photo_save_path(
    file: UploadFile = File(...),
    context: str = Form(""),
    current_user: User = Depends(get_current_user),
) -> dict:  # type: ignore[type-arg]
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Photo too large (max 10MB)")

    analysis = await gemini_adapter.analyze_photo(
        image_bytes, mime_type=file.content_type or "image/jpeg", context=context
    )
    photo_path = photo_storage.save(image_bytes)

    return {
        "description": analysis.description,
        "nutrition": {
            "calories": analysis.nutrition.calories,
            "protein_g": analysis.nutrition.protein_g,
            "fat_g": analysis.nutrition.fat_g,
            "carbs_g": analysis.nutrition.carbs_g,
            "portion_g": analysis.nutrition.portion_g,
        },
        "confidence": analysis.confidence,
        "notes": analysis.notes,
        "photo_path": photo_path,
        "gemini_raw": analysis.gemini_raw,
    }


@router.post("/text", response_model=MealAnalysisResponse)
async def analyze_text(
    body: MealTextRequest,
    current_user: User = Depends(get_current_user),
) -> MealAnalysisResponse:
    analysis = await gemini_adapter.analyze_text(body.description)
    return MealAnalysisResponse(
        description=analysis.description,
        nutrition=NutritionFactsSchema(
            calories=analysis.nutrition.calories,
            protein_g=analysis.nutrition.protein_g,
            fat_g=analysis.nutrition.fat_g,
            carbs_g=analysis.nutrition.carbs_g,
            portion_g=analysis.nutrition.portion_g,
        ),
        confidence=analysis.confidence,
        notes=analysis.notes,
    )


@router.post("/voice", response_model=MealAnalysisResponse)
async def analyze_voice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> MealAnalysisResponse:
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio type")

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Audio too large (max 10MB)")

    analysis = await gemini_adapter.analyze_voice(audio_bytes, mime_type=file.content_type or "audio/ogg")
    return MealAnalysisResponse(
        description=analysis.description,
        nutrition=NutritionFactsSchema(
            calories=analysis.nutrition.calories,
            protein_g=analysis.nutrition.protein_g,
            fat_g=analysis.nutrition.fat_g,
            carbs_g=analysis.nutrition.carbs_g,
            portion_g=analysis.nutrition.portion_g,
        ),
        confidence=analysis.confidence,
        notes=analysis.notes,
    )


@router.post("/confirm", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
async def confirm_meal(
    body: MealConfirmRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealResponse:
    repo = MealRepo(session)
    meal = MealEntry(
        user_id=current_user.telegram_id,
        description=body.description,
        nutrition=NutritionFacts(
            calories=body.nutrition.calories,
            protein_g=body.nutrition.protein_g,
            fat_g=body.nutrition.fat_g,
            carbs_g=body.nutrition.carbs_g,
            portion_g=body.nutrition.portion_g,
        ),
        confidence=body.confidence,
        photo_path=body.photo_path,
        gemini_raw=body.gemini_raw,
        confirmed=True,
        logged_at=datetime.now(timezone.utc),
    )
    saved = await repo.save(meal)
    return _meal_to_response(saved)


@router.patch("/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: uuid.UUID,
    body: MealUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealResponse:
    repo = MealRepo(session)
    nutrition = None
    if body.nutrition is not None:
        nutrition = NutritionFacts(
            calories=body.nutrition.calories,
            protein_g=body.nutrition.protein_g,
            fat_g=body.nutrition.fat_g,
            carbs_g=body.nutrition.carbs_g,
            portion_g=body.nutrition.portion_g,
        )
    updated = await repo.update(
        meal_id=meal_id,
        user_id=current_user.telegram_id,
        description=body.description,
        nutrition=nutrition,
        confidence=body.confidence,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return _meal_to_response(updated)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    repo = MealRepo(session)
    deleted = await repo.delete(meal_id, current_user.telegram_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")


def _meal_to_response(meal: MealEntry) -> MealResponse:
    return MealResponse(
        id=meal.id,
        description=meal.description,
        nutrition=NutritionFactsSchema(
            calories=meal.nutrition.calories,
            protein_g=meal.nutrition.protein_g,
            fat_g=meal.nutrition.fat_g,
            carbs_g=meal.nutrition.carbs_g,
            portion_g=meal.nutrition.portion_g,
        ),
        confidence=meal.confidence,
        photo_path=meal.photo_path,
        logged_at=meal.logged_at,
        confirmed=meal.confirmed,
    )
