from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação — única fonte de verdade (lê do ambiente / .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "bussola-api"

    # Conexão usada pela app. No compose vem como DATABASE_URL apontando p/ host=postgres.
    database_url: str = "postgresql+asyncpg://bussola:bussola@localhost:5432/bussola"

    # Stores auxiliares — só consumidos em runtime nas fatias seguintes.
    qdrant_url: str = "http://localhost:6333"
    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "corpus"


@lru_cache
def get_settings() -> Settings:
    """Instância única e cacheada das configurações (evita reler o ambiente a cada chamada)."""
    return Settings()
