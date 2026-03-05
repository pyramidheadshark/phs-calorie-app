from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from calorie_app.api import meals, logs, settings as settings_router, webhook, recipes as recipes_router
from calorie_app.adapters.db.session import engine
from calorie_app.config import settings

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting calorie-app (model: %s)", settings.openrouter_model)
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="PHS Calorie App",
    description="Telegram Mini App calorie tracker with Gemini Vision",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meals.router)
app.include_router(logs.router)
app.include_router(settings_router.router)
app.include_router(recipes_router.router)
app.include_router(webhook.router)


@app.get("/health")
async def health() -> dict:  # type: ignore[type-arg]
    return {"status": "ok", "model": settings.openrouter_model}


_frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
