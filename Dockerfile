FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_PROGRESS=1 \
    UV_SYSTEM_PYTHON=1

RUN pip install uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY src/ ./src/

CMD ["uvicorn", "calorie_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
