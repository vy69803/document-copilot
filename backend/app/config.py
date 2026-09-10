import os
from functools import cached_property
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Environment ---
    environment: str = "development"

    # --- Supabase (Auth + DB) ---
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # --- Postgres (Alembic + direct DB access) ---
    database_url: str

    # --- LLM & Embeddings (Gemini / OpenAI) ---
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768

    # Legacy / OpenAI aliases if specified in .env
    openai_embedding_model: str | None = None
    openai_embedding_dimensions: int | None = None

    # --- Server / CORS ---
    # Comma-separated list in .env; parsed by the `cors_origins` property
    allowed_origins: str = "http://localhost:5173"

    @cached_property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Returns database URL using the psycopg (v3) driver for SQLAlchemy."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    @model_validator(mode="after")
    def validate_keys_and_mirror_env(self) -> Self:
        # Require at least one LLM key
        if not self.gemini_api_key and not self.openai_api_key:
            raise ValueError(
                "Either GEMINI_API_KEY or OPENAI_API_KEY must be configured in environment."
            )

        # Mirror keys to os.environ for SDKs (e.g. PydanticAI / Google / OpenAI)
        if self.gemini_api_key:
            os.environ.setdefault("GEMINI_API_KEY", self.gemini_api_key)
            os.environ.setdefault("GOOGLE_API_KEY", self.gemini_api_key)

        if self.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.openai_api_key)

        return self


settings = Settings()  # type: ignore[call-arg]

