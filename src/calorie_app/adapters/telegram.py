from __future__ import annotations

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl, unquote

import httpx

from calorie_app.config import settings

logger = logging.getLogger(__name__)

BOT_API_URL = "https://api.telegram.org/bot{token}/{method}"


def validate_init_data(init_data: str) -> dict:  # type: ignore[type-arg]
    parsed = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash in initData")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(
        b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256
    ).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid initData signature")

    return json.loads(parsed["user"])


class TelegramBot:
    def __init__(self) -> None:
        self._token = settings.telegram_bot_token
        self._app_url = settings.app_url

    def _url(self, method: str) -> str:
        return BOT_API_URL.format(token=self._token, method=method)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,  # type: ignore[type-arg]
    ) -> bool:
        payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}  # type: ignore[type-arg]
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(self._url("sendMessage"), json=payload)
                resp.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error("Telegram sendMessage failed: %s", e)
                return False

    async def send_reminder(self, chat_id: int, text: str) -> bool:
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📱 Открыть дневник",
                        "web_app": {"url": self._app_url},
                    }
                ]
            ]
        }
        return await self.send_message(chat_id, text, reply_markup=keyboard)

    async def send_daily_summary(
        self,
        chat_id: int,
        calories: int,
        target: int,
        protein_g: float,
        fat_g: float,
        carbs_g: float,
        water_ml: int,
        water_target_ml: int,
    ) -> bool:
        text = (
            f"📊 <b>Итоги дня</b>\n\n"
            f"🔥 Калории: <b>{calories}</b> из {target} ккал\n"
            f"💪 Белки: <b>{protein_g:.0f} г</b>\n"
            f"🥑 Жиры: <b>{fat_g:.0f} г</b>\n"
            f"🌾 Углеводы: <b>{carbs_g:.0f} г</b>\n"
            f"💧 Вода: <b>{water_ml} мл</b> из {water_target_ml} мл"
        )
        return await self.send_reminder(chat_id, text)

    async def set_webhook(self, webhook_url: str) -> bool:
        payload = {
            "url": webhook_url,
            "secret_token": settings.telegram_webhook_secret,
            "allowed_updates": ["message", "callback_query"],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(self._url("setWebhook"), json=payload)
                resp.raise_for_status()
                data = resp.json()
                logger.info("Webhook set: %s", data.get("description"))
                return data.get("ok", False)
            except httpx.HTTPError as e:
                logger.error("setWebhook failed: %s", e)
                return False


telegram_bot = TelegramBot()
