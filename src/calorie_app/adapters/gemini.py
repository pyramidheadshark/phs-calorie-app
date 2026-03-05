from __future__ import annotations

import base64
import json
import logging

import httpx

from calorie_app.adapters.prompts import (
    ANALYSIS_PROMPT,
    PROFILE_PARSE_PROMPT,
    RECIPE_PROMPT,
    TEXT_ANALYSIS_PROMPT,
    VOICE_ANALYSIS_PROMPT,
)
from calorie_app.config import settings
from calorie_app.core.domain import Confidence, NutritionAnalysis, NutritionFacts, RecipeEntry

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class GeminiAdapter:
    def __init__(self) -> None:
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.app_url,
            "X-Title": "phs-calorie-app",
        }

    async def _post(self, payload: dict, timeout: float = 30.0) -> dict:  # type: ignore[type-arg]
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_URL, json=payload, headers=self._headers())
            response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    @staticmethod
    def _strip_fences(content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return cleaned

    def _parse_response(self, content: str) -> NutritionAnalysis:
        try:
            cleaned = self._strip_fences(content)
            data = json.loads(cleaned)
            confidence: Confidence = data.get("confidence", "medium")
            if confidence not in ("high", "medium", "low"):
                confidence = "medium"

            return NutritionAnalysis(
                description=str(data.get("description", "Блюдо")),
                nutrition=NutritionFacts(
                    calories=int(data.get("calories", 0)),
                    protein_g=float(data.get("protein_g", 0)),
                    fat_g=float(data.get("fat_g", 0)),
                    carbs_g=float(data.get("carbs_g", 0)),
                    portion_g=int(data.get("portion_g", 0)),
                ),
                confidence=confidence,
                notes=str(data.get("notes", "")),
                gemini_raw=data,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse Gemini response: %s. Content: %s", e, content[:200])
            return NutritionAnalysis(
                description="Не удалось распознать блюдо",
                nutrition=NutritionFacts(),
                confidence="low",
                notes="Ошибка парсинга ответа AI",
                gemini_raw={"raw": content},
            )

    async def analyze_photo(
        self, image_bytes: bytes, mime_type: str = "image/jpeg", context: str = ""
    ) -> NutritionAnalysis:
        b64 = base64.b64encode(image_bytes).decode()
        data_url = f"data:{mime_type};base64,{b64}"

        prompt_text = ANALYSIS_PROMPT
        if context:
            prompt_text += f"\nAdditional context from user: {context}"

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": prompt_text},
                    ],
                }
            ],
            "max_tokens": 500,
        }

        body = await self._post(payload)
        return self._parse_response(body["choices"][0]["message"]["content"])

    async def analyze_text(self, description: str) -> NutritionAnalysis:
        prompt = TEXT_ANALYSIS_PROMPT.format(description=description)
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
        }
        body = await self._post(payload, timeout=20.0)
        return self._parse_response(body["choices"][0]["message"]["content"])

    async def analyze_voice(self, audio_bytes: bytes, mime_type: str = "audio/ogg") -> NutritionAnalysis:
        ext = mime_type.split("/")[-1]
        b64 = base64.b64encode(audio_bytes).decode()

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": b64, "format": ext},
                        },
                        {"type": "text", "text": VOICE_ANALYSIS_PROMPT},
                    ],
                }
            ],
            "max_tokens": 500,
        }

        body = await self._post(payload)
        return self._parse_response(body["choices"][0]["message"]["content"])

    async def parse_profile(self, profile_text: str) -> dict:  # type: ignore[type-arg]
        prompt = PROFILE_PARSE_PROMPT.format(profile_text=profile_text)
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
        }
        body = await self._post(payload)
        content = self._strip_fences(body["choices"][0]["message"]["content"])
        return json.loads(content)  # type: ignore[no-any-return]

    async def generate_recipe(
        self,
        user_id: int,
        goal: str,
        calorie_target: int,
        protein_g: int,
        fat_g: int,
        carbs_g: int,
        preferences: str,
        equipment: list[str],
        liked_titles: list[str],
        disliked_titles: list[str],
    ) -> RecipeEntry:
        prompt = RECIPE_PROMPT.format(
            goal=goal or "здоровое питание",
            calories=calorie_target,
            protein=protein_g,
            fat=fat_g,
            carbs=carbs_g,
            preferences=preferences or "без ограничений",
            equipment=", ".join(equipment) if equipment else "стандартная кухня",
            liked=", ".join(liked_titles) if liked_titles else "нет данных",
            disliked=", ".join(disliked_titles) if disliked_titles else "нет",
        )
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
        }
        body = await self._post(payload, timeout=45.0)
        content = self._strip_fences(body["choices"][0]["message"]["content"])
        data = json.loads(content)
        n = data.get("nutrition_estimate", {})
        return RecipeEntry(
            user_id=user_id,
            title=str(data.get("title", "Рецепт")),
            description=str(data.get("description", "")),
            ingredients=data.get("ingredients", []),
            instructions=data.get("instructions", []),
            nutrition_estimate=NutritionFacts(
                calories=int(n.get("calories", 0)),
                protein_g=float(n.get("protein_g", 0)),
                fat_g=float(n.get("fat_g", 0)),
                carbs_g=float(n.get("carbs_g", 0)),
                portion_g=int(n.get("portion_g", 0)),
            ),
            cooking_time_min=int(data.get("cooking_time_min", 30)),
            equipment_used=data.get("equipment_used", []),
        )


gemini_adapter = GeminiAdapter()
