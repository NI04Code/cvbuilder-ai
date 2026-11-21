"""Application configuration via pydantic-settings."""

from pathlib import Path
from typing import Any, Literal
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

    # ── Runtime Environment & Logging ─────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://cvbuilder:cvbuilder_secret@localhost:5433/cvbuilder_db"

    # ── JWT & Internal Auth ───────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    internal_auth_secret: str = ""
    oauth_token_encryption_key: str = ""

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

    # ── Groq ──────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_max_tokens: int = 8192
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 2
    groq_fallback_models: str | list[str] = [
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
    ]

    @field_validator("gemini_fallback_models", "groq_fallback_models", mode="after")
    @classmethod
    def parse_fallback_models(cls, v: Any) -> list[str]:
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

    def validate_production_secrets(self) -> None:
        """Fail fast if insecure default secrets are used in production."""
        if self.environment != "production":
            return
        if self.jwt_secret_key == "CHANGE-ME-IN-PRODUCTION" or len(self.jwt_secret_key) < 32:
            raise RuntimeError(
                "Insecure JWT_SECRET_KEY in production: must be at least 32 characters and not the default placeholder."
            )
        if not self.internal_auth_secret or len(self.internal_auth_secret) < 16:
            raise RuntimeError(
                "Missing or weak INTERNAL_AUTH_SECRET in production: must be at least 16 characters."
            )
        if not self.oauth_token_encryption_key:
            raise RuntimeError(
                "Missing OAUTH_TOKEN_ENCRYPTION_KEY in production: must be set to a valid Fernet key."
            )


settings = Settings()
