import json
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_NAME: str = "CASTLEWEB API"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    ENABLE_DOCS: bool = True

    # Security
    SECRET_KEY: str = "super-secret-castleweb-key-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,https://castleweb.ru"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./castleweb.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram Bot (Headless CRM)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_API_BASE_URL: str = Field(
        default="https://api.telegram.org/bot",
        validation_alias=AliasChoices("TELEGRAM_API_BASE_URL", "TELEGRAM_PROXY_URL")
    )

    # Cloudflare Turnstile
    CLOUDFLARE_TURNSTILE_SECRET_KEY: str = Field(
        default="1x0000000000000000000000000000000AA",
        validation_alias=AliasChoices("CLOUDFLARE_TURNSTILE_SECRET_KEY", "TURNSTILE_SECRET_KEY")
    )
    CLOUDFLARE_TURNSTILE_ENABLED: bool = False

    # Storage Driver (local or r2)
    STORAGE_DRIVER: str = "local"
    UPLOAD_DIR: str = "/uploads"

    # Cloudflare R2 / S3
    R2_ACCOUNT_ID: str = Field(
        default="",
        validation_alias=AliasChoices("R2_ACCOUNT_ID", "CLOUDFLARE_R2_ACCOUNT_ID")
    )
    R2_ACCESS_KEY_ID: str = Field(
        default="",
        validation_alias=AliasChoices("R2_ACCESS_KEY_ID", "CLOUDFLARE_R2_ACCESS_KEY_ID")
    )
    R2_SECRET_ACCESS_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("R2_SECRET_ACCESS_KEY", "CLOUDFLARE_R2_SECRET_ACCESS_KEY")
    )
    R2_BUCKET_NAME: str = Field(
        default="castleweb-uploads",
        validation_alias=AliasChoices("R2_BUCKET_NAME", "CLOUDFLARE_R2_BUCKET_NAME")
    )
    R2_PUBLIC_DOMAIN: str = Field(
        default="",
        validation_alias=AliasChoices("R2_PUBLIC_DOMAIN", "CLOUDFLARE_R2_PUBLIC_URL", "R2_PUBLIC_URL")
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["*"]
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
        return [origin.strip().strip("'\"[]") for origin in raw.split(",") if origin.strip().strip("'\"[]")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

