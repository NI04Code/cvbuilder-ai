"""Application configuration via pydantic-settings."""

from pathlib import Path
from typing import Any
import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://cvbuilder:cvbuilder_secret@localhost:5433/cvbuilder_db"

    # ── JWT ───────────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── Google Gemini ─────────────────────────────────────────────────────
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_models: str | list[str] = [
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
    ]

    @field_validator("gemini_fallback_models", mode="after")
    @classmethod
    def parse_gemini_fallback_models(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            val = v.strip()
            if val.startswith("["):
                return json.loads(val)
            return [m.strip() for m in val.split(",") if m.strip()]
        return v

    # ── File Storage ──────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    generated_dir: str = "generated"
    max_upload_size_mb: int = 10

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_path(self) -> Path:
        path = Path(self.generated_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
