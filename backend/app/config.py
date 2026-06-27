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

    app_name: str = "workshop-api"

    # Conexão usada pela app. No compose vem como DATABASE_URL apontando p/ host=postgres:5432
    # (rede interna). Este default é só fallback p/ rodar no host — onde o Postgres é publicado
    # na 5433 (POSTGRES_PORT do .env do workshop), evitando colidir com outra stack na 5432.
    database_url: str = "postgresql+asyncpg://workshop:workshop@localhost:5433/workshop"

    # Stores auxiliares — só consumidos em runtime nas fatias seguintes.
    qdrant_url: str = "http://localhost:6333"
    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "corpus"


@lru_cache
def get_settings() -> Settings:
    """Instância única e cacheada das configurações (evita reler o ambiente a cada chamada)."""
    return Settings()
