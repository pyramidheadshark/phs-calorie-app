from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from calorie_app.adapters.telegram import telegram_bot
from calorie_app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict:  # type: ignore[type-arg]
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    update = await request.json()
    logger.debug("Telegram update: %s", update)

    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    if text == "/start":
        await telegram_bot.send_message(
            chat_id,
            "👋 Привет! Я помогу отслеживать калории.\n\nОткрой дневник, чтобы начать:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📱 Открыть дневник", "web_app": {"url": settings.app_url}}]
                ]
            },
        )
    elif text == "/help":
        await telegram_bot.send_message(
            chat_id,
            "📖 <b>Как пользоваться:</b>\n\n"
            "1. Открой дневник через кнопку\n"
            "2. Сфотографируй блюдо\n"
            "3. ИИ определит КБЖУ автоматически\n"
            "4. Подтверди или отредактируй\n\n"
            "💧 Также можно логировать воду прямо в приложении.",
        )

    return {"ok": True}
