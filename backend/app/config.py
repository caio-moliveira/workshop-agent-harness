"""Configuracao da aplicacao (issue #15).

Le do ambiente via pydantic-settings; nunca hardcode segredo. No container, o
docker-compose injeta DATABASE_URL apontando para o host `postgres`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Conexao admin (RW) do app. Sobrescrita pelo ambiente (DATABASE_URL).
    database_url: str = "postgresql+asyncpg://bussola:bussola@postgres:5432/bussola"


settings = Settings()
