.PHONY: install dev run lint test docker-up docker-down docker-logs

install:
	uv sync

dev:
	uv sync --dev

run:
	uv run uvicorn calorie_app.main:app --reload --host 0.0.0.0 --port 8001

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check . --fix

test:
	uv run pytest -x -v

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f bot
