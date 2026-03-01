# Project Status

> **IMPORTANT**: This file is loaded at the start of every Claude Code session.
> Keep it accurate. Update it before ending any session.
> This is the single source of truth for project state.

---

## Business Goal

Telegram-бот для личного учёта питания: пользователь описывает еду в свободной форме, бот возвращает КБЖУ через LLM (OpenRouter).

---

## Current Phase

- [x] Phase 0: Intake & Requirements
- [ ] Phase 1: Design Document
- [x] Phase 2: Environment Setup
- [x] Phase 3: Development Loop — базовый шаблон готов
- [ ] Phase 4: API Layer & Testing
- [ ] Phase 5: CI/CD
- [ ] Phase 6: Deploy

**Active phase**: Phase 3 — шаблон готов, нужен BOT_TOKEN для запуска

---

## Backlog

- [ ] Получить BOT_TOKEN через @BotFather → заполнить `.env`
- [ ] `make install` → `make run` → ручное тестирование
- [ ] Решить: нужна ли история приёмов пищи (SQLite + aiosqlite)
- [ ] Написать тесты (mock aiogram Message)
- [ ] Опционально: поддержка фото еды (Vision API)

**Completed:**
- [x] Базовая структура проекта (config, ai, handlers, main) — 2026-03-04
- [x] ml-claude-infra задеплоен — 2026-03-04

---

## Architecture Decisions

| Decision | Choice | Date |
|---|---|---|
| LLM provider | OpenRouter (google/gemini-2.5-flash) | 2026-03-04 |
| State | Stateless (нет БД) | 2026-03-04 |
| Bot framework | aiogram 3.x (async) | 2026-03-04 |

---

## Next Session Plan

1. Заполнить BOT_TOKEN, запустить `make run`
2. Протестировать несколько запросов вручную
3. Решить про историю питания

---

## Files to Know

| File | Purpose |
|---|---|
| `src/phs_calorie_app/config.py` | Settings (BOT_TOKEN, OPENROUTER_API_KEY, AI_MODEL) |
| `src/phs_calorie_app/ai.py` | OpenRouter вызов, SYSTEM_PROMPT |
| `src/phs_calorie_app/handlers.py` | aiogram Router: /start, /help, текстовые сообщения |
| `src/phs_calorie_app/main.py` | Точка входа, polling |

---

*Last updated: 2026-03-04 by Claude Code*
