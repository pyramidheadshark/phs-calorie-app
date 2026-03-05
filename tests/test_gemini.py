from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calorie_app.adapters.gemini import GeminiAdapter
from calorie_app.adapters.prompts import ANALYSIS_PROMPT, TEXT_ANALYSIS_PROMPT


@pytest.fixture()
def adapter() -> GeminiAdapter:
    return GeminiAdapter()


class TestStripFences:
    def test_plain_json(self, adapter: GeminiAdapter) -> None:
        assert adapter._strip_fences('{"calories": 300}') == '{"calories": 300}'

    def test_json_in_backtick_fence(self, adapter: GeminiAdapter) -> None:
        content = "```\n{\"calories\": 300}\n```"
        assert adapter._strip_fences(content) == '{"calories": 300}'

    def test_json_in_named_fence(self, adapter: GeminiAdapter) -> None:
        content = "```json\n{\"calories\": 300}\n```"
        assert adapter._strip_fences(content) == '{"calories": 300}'

    def test_no_trailing_fence(self, adapter: GeminiAdapter) -> None:
        content = "```json\n{\"calories\": 300}"
        assert "calories" in adapter._strip_fences(content)

    def test_strips_whitespace(self, adapter: GeminiAdapter) -> None:
        assert adapter._strip_fences('  {"calories": 300}  ') == '{"calories": 300}'


class TestParseResponse:
    def test_valid_json(self, adapter: GeminiAdapter) -> None:
        content = json.dumps({
            "description": "Борщ", "calories": 250, "protein_g": 10.0,
            "fat_g": 5.0, "carbs_g": 35.0, "portion_g": 400,
            "confidence": "high", "notes": "традиционный",
        })
        result = adapter._parse_response(content)
        assert result.description == "Борщ"
        assert result.nutrition.calories == 250
        assert result.confidence == "high"

    def test_fenced_json(self, adapter: GeminiAdapter) -> None:
        data = {"description": "Суп", "calories": 150, "protein_g": 8.0,
                "fat_g": 3.0, "carbs_g": 20.0, "portion_g": 300,
                "confidence": "medium", "notes": ""}
        result = adapter._parse_response(f"```json\n{json.dumps(data)}\n```")
        assert result.nutrition.calories == 150

    def test_unknown_confidence_becomes_medium(self, adapter: GeminiAdapter) -> None:
        content = json.dumps({
            "description": "Блюдо", "calories": 100, "protein_g": 5.0,
            "fat_g": 2.0, "carbs_g": 15.0, "portion_g": 200,
            "confidence": "unknown", "notes": "",
        })
        assert adapter._parse_response(content).confidence == "medium"

    def test_invalid_json_returns_fallback(self, adapter: GeminiAdapter) -> None:
        result = adapter._parse_response("not valid json at all")
        assert result.confidence == "low"
        assert result.description == "Не удалось распознать блюдо"
        assert result.nutrition.calories == 0

    def test_partial_json_uses_defaults(self, adapter: GeminiAdapter) -> None:
        result = adapter._parse_response('{"description": "Яблоко"}')
        assert result.description == "Яблоко"
        assert result.nutrition.calories == 0
        assert result.confidence == "medium"


class TestPromptConstants:
    """Verify that prompts contain expected schema fields."""

    def test_analysis_prompt_has_required_fields(self) -> None:
        for field in ("calories", "protein_g", "fat_g", "carbs_g", "confidence"):
            assert field in ANALYSIS_PROMPT

    def test_text_analysis_prompt_has_description_placeholder(self) -> None:
        assert "{description}" in TEXT_ANALYSIS_PROMPT

    def test_text_analysis_prompt_formats(self) -> None:
        filled = TEXT_ANALYSIS_PROMPT.format(description="борщ со сметаной")
        assert "борщ со сметаной" in filled


class TestAnalyzeText:
    async def test_returns_nutrition(self, adapter: GeminiAdapter) -> None:
        mock_data = {
            "description": "Гречка с курицей", "calories": 400,
            "protein_g": 30.0, "fat_g": 10.0, "carbs_g": 45.0,
            "portion_g": 350, "confidence": "medium", "notes": "",
        }
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(mock_data)}}]
        }
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("calorie_app.adapters.gemini.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.analyze_text("гречка с курицей 350г")

        assert result.description == "Гречка с курицей"
        assert result.nutrition.calories == 400
        assert result.nutrition.protein_g == 30.0

    async def test_propagates_http_error(self, adapter: GeminiAdapter) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock(status_code=500)
        ))

        with patch("calorie_app.adapters.gemini.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await adapter.analyze_text("борщ")
