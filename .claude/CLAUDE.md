# phs-calorie-app

Telegram Mini App для учёта КБЖУ. Пользователь фотографирует еду, описывает текстом или голосом — FastAPI бэкенд вызывает Gemini через OpenRouter и возвращает калории/белки/жиры/углеводы.

## Stack

- **FastAPI + uvicorn** — async HTTP API, порт 8001
- **OpenRouter** — LLM API, модель: `google/gemini-3-flash-preview`
- **PostgreSQL + SQLAlchemy asyncpg** — хранение приёмов пищи, пользователей, рецептов
- **Alembic** — миграции
- **Celery + Redis** — фоновые задачи (очистка фото, дневные сводки)
- **uv** — менеджер пакетов
- **Docker Compose** — полный стек

## Structure

```
src/calorie_app/
    adapters/
        db/repos.py     — MealRepo, UserRepo, RecipeRepo
        gemini.py       — GeminiAdapter (analyze_photo/text/voice, parse_profile, generate_recipe)
        prompts.py      — все системные промпты как константы
        storage.py      — сохранение фото на диск (/app/photos volume)
        telegram.py     — TelegramBot, validate_init_data (HMAC-SHA256)
    api/
        deps.py         — get_current_user: валидация x-telegram-init-data → User
        ratelimit.py    — check_ai_rate_limit: 30 req/hour/user через Redis
        meals.py        — /api/meal/* (photo-path, text, voice, confirm, PATCH, DELETE)
        logs.py         — /api/daily, /api/history, /api/stats/*
        recipes.py      — /api/recipes (generate, history, feedback)
        settings.py     — /api/user/settings, /api/user/profile/parse
        webhook.py      — /webhook/telegram (/start, /help → Web App кнопка)
    core/
        domain.py       — MealEntry, User, UserSettings, DailyLog, RecipeEntry и др.
        calculator.py   — compute_streak, macro_percentages, calorie_progress
    models/schemas.py   — Pydantic-схемы (запросы и ответы)
    config.py           — Settings из .env (env_file=".env")
    main.py             — FastAPI app, роутеры
    worker.py           — Celery tasks: cleanup_photos, send_daily_summaries
```

## Key decisions

- **Аутентификация**: `x-telegram-init-data` header, HMAC-SHA256 по `BOT_TOKEN`, без сессий
- **Rate limit**: `check_ai_rate_limit` dependency на AI-эндпоинтах; fail-open если Redis недоступен
- **Фото**: volume `/app/photos`, путь в БД, Celery удаляет через 24 часа
- **UserSettings**: хранятся как JSONB в `users.settings` — без миграций при добавлении полей
- **Промпты**: только в `adapters/prompts.py`, `gemini.py` их импортирует

## Run

```bash
# Docker (полный стек)
docker compose up -d --build
docker compose exec api uv run alembic upgrade head

# Локально
uv sync
uv run uvicorn calorie_app.main:app --reload --port 8001

# Тесты
uv sync --dev
uv run python -m pytest -x -v
```

## .env (минимум)

```
OPENROUTER_API_KEY=sk-or-...
TELEGRAM_BOT_TOKEN=...
APP_URL=https://your-domain.com
POSTGRES_URL=postgresql+asyncpg://calorie:secret@postgres:5432/calorie_dev
REDIS_URL=redis://redis:6379/0
```

## Что НЕ реализовано

- Водный трекер — удалён намеренно
- Фронтенд — отдаётся из `frontend/dist/` если папка существует; разработка отдельно
- Voice-эндпоинт работает через OpenRouter multimodal audio; не все модели поддерживают
