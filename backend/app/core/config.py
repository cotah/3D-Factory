"""Application settings loaded from environment variables (.env).

Uses pydantic-settings. Field names map to environment variables
case-insensitively (e.g. the field ``database_url`` reads ``DATABASE_URL``).
Unknown variables in the .env are ignored so the file can hold extra keys.
"""

from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env lives at the project root, but the backend is normally started from
# the ``backend/`` directory (per the README). Resolve the root .env by absolute
# path so settings load no matter the current working directory. A local
# ``.env`` (next to the CWD) still wins if present, for overrides.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ROOT_ENV = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "Print3D Platform"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"
    allowed_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://print3d:print3d@localhost:5432/print3d"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ---- Redis / Celery ----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ---- Auth / JWT ----
    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ---- Anthropic ----
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-20250514"
    claude_max_tokens: int = 4096

    # ---- OpenAI ----
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-2"
    openai_image_size: str = "1024x1024"
    openai_image_quality: str = "high"

    # ---- RunPod ----
    runpod_api_key: str = ""
    runpod_trellis_endpoint_id: str = ""
    runpod_timeout_seconds: int = 300
    runpod_webhook_secret: str = ""

    # ---- Storage ----
    storage_provider: str = "r2"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket: str = "print3d-assets"
    storage_region: str = "auto"
    storage_endpoint_url: str = ""
    storage_public_url: str = ""
    upload_max_file_size_mb: int = 50
    # Raw CSV string from env; use ``allowed_extensions`` for the parsed set.
    upload_allowed_extensions: str = "png,jpg,jpeg,webp,glb,obj,stl,zip"
    # Where uploaded files are stored locally in Phase 1 (real S3/R2 in Phase 2).
    upload_dir: str = os.path.join(tempfile.gettempdir(), "print3d_uploads")
    # Local on-disk storage dir served via /static (Phase 3 LocalStorageService).
    local_storage_dir: str = "local_storage"
    # Public base URL the frontend uses to fetch files served from /static.
    static_base_url: str = "http://localhost:8000/static"

    # ---- Email ----
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@print3d.local"
    smtp_from_name: str = "Print3D Platform"

    # ---- Stripe ----
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # ---- Mock mode ----
    ai_mock_mode: bool = True
    runpod_mock_mode: bool = True
    storage_mock_mode: bool = False

    # ---- Sentry ----
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1

    # ---- Admin seed ----
    admin_email: str = "admin@print3d.com"
    admin_password: str = "admin123"
    admin_name: str = "Admin"

    # ---- Frontend ----
    next_public_api_url: str = "http://localhost:8000/api/v1"
    next_public_app_url: str = "http://localhost:3000"

    # -------- Derived helpers --------
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            e.strip().lower().lstrip(".")
            for e in self.upload_allowed_extensions.split(",")
            if e.strip()
        }

    @property
    def upload_max_bytes(self) -> int:
        return self.upload_max_file_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
