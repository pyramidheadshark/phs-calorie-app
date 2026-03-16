# phs-calorie-app

Telegram Mini App for meal logging — photograph or describe food, get calories and macros via Gemini Vision.

![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/fastapi-0.115%2B-009688?style=flat-square)
![React](https://img.shields.io/badge/react-18-61dafb?style=flat-square)
[![CI](https://github.com/pyramidheadshark/phs_calorie_app/actions/workflows/ci.yml/badge.svg?style=flat-square)](https://github.com/pyramidheadshark/phs_calorie_app/actions/workflows/ci.yml)

---

## Overview

**Problem:** Manual calorie counting is too slow to sustain in practice — opening a food database to log every meal kills the habit.

**Solution:** Open the Mini App inside Telegram, snap a photo or type what you ate. Gemini Vision identifies the meal and returns calories, protein, fat, and carbs in seconds. Results go into a persistent diary with history, streak tracking, analytics, recipe generation, and a conversational AI assistant.

> This project was written entirely by a Claude AI agent using presets and infrastructure from [pyramidheadshark/ml-claude-infra](https://github.com/pyramidheadshark/ml-claude-infra). Code, tests, migrations, and Docker config were generated in agentic sessions without manual coding.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + uvicorn |
| AI | OpenRouter → Gemini 2.5 Flash |
| Database | PostgreSQL + SQLAlchemy asyncpg |
| Migrations | Alembic |
| Background tasks | Celery + Redis |
| Frontend | React (Telegram Mini App) |
| Auth | Telegram initData HMAC-SHA256 |
| Infra | Docker Compose, uv |

---

## Features

- **Photo recognition** — snap a meal, get calories and macros from Gemini Vision
- **Text and voice input** — describe food in free text or send a voice message
- **Daily diary** — log, edit, and delete meals; see daily totals vs. targets
- **History and streaks** — browse past days, track consecutive logging streaks
- **Analytics** — 30-day calorie trend, weekly macro breakdown, top dishes
- **Recipe generation** — personalized recipes based on goals and kitchen equipment
- **AI chat assistant** — conversational assistant aware of today's meals and weekly stats
- **Profile parsing** — calorie and macro targets inferred from a free-text description

---

## Getting Started

### 1. Environment

Create `.env` in the project root:

```env
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemini-2.5-flash
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_WEBHOOK_SECRET=your-secret
APP_URL=https://your-domain.com
POSTGRES_URL=postgresql+asyncpg://calorie:secret@postgres:5432/calorie_dev
POSTGRES_SYNC_URL=postgresql+psycopg2://calorie:secret@postgres:5432/calorie_dev
REDIS_URL=redis://redis:6379/0
```

### 2. Docker Compose

```bash
docker compose up -d --build
docker compose exec api uv run alembic upgrade head
curl http://localhost:8001/health
```

Telegram webhook and Mini App button are registered automatically on startup.

### 3. Local (API only)

```bash
uv sync
uv run uvicorn calorie_app.main:app --reload --port 8001
```

Requires local PostgreSQL and Redis.

### 4. Tests

```bash
uv sync --dev
uv run pytest -x -v
```

98 unit tests, no running services required — all external dependencies are mocked. Coverage 85%.

---

## API

All `/api/*` endpoints require `x-telegram-init-data` header (HMAC-SHA256, verified against `BOT_TOKEN`).
AI endpoints are rate-limited to 30 requests/hour per user via Redis.

| Endpoint | Description |
|----------|-------------|
| `POST /api/meal/photo-path` | Photo → Gemini Vision → calories + macros |
| `POST /api/meal/text` | Text description → calories + macros |
| `POST /api/meal/voice` | Audio (ogg/mp3/wav/aac) → calories + macros |
| `POST /api/meal/confirm` | Save a meal entry to diary |
| `PATCH /api/meal/{id}` | Edit meal description or nutrition |
| `DELETE /api/meal/{id}` | Delete a meal entry |
| `GET /api/daily/{date}` | Daily log with totals |
| `GET /api/history` | Paginated history |
| `GET /api/stats/streak` | Consecutive logging days |
| `GET /api/stats/analytics` | 30-day trend, macro split, top dishes |
| `POST /api/chat` | AI assistant with daily meal context |
| `POST /api/recipes/generate` | Personalized recipe generation |

---

## На русском

Telegram Mini App для учёта КБЖУ с AI-распознаванием еды.

Сфотографируй блюдо, опиши текстом или голосом — приложение вернёт калории, белки, жиры и углеводы через Gemini Vision. Данные сохраняются в дневник с историей, стриками, аналитикой, генератором рецептов и AI-ассистентом.

Стек: FastAPI + PostgreSQL + Celery + Redis + React (Telegram Mini App).

Проект написан целиком AI-агентом (Claude) по пресетам из [ml-claude-infra](https://github.com/pyramidheadshark/ml-claude-infra).
