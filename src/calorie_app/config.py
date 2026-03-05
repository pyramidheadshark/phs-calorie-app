from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = "postgresql+asyncpg://calorie:secret@localhost:5432/calorie_dev"
    postgres_sync_url: str = "postgresql+psycopg2://calorie:secret@localhost:5432/calorie_dev"
    redis_url: str = "redis://localhost:6379/0"

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-3-flash-preview"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = "dev-secret"

    app_port: int = 8001
    app_url: str = "https://example.com"
    photo_storage_path: str = "/app/photos"
    photo_max_age_hours: int = 24
    debug: bool = False


settings = Settings()
