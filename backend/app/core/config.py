"""Configuração da aplicação (12-factor): lida de variáveis de ambiente / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Bússola API"
    # Conexão admin (RW). O papel somente-leitura do agente entra em issue posterior.
    database_url: str = "postgresql+asyncpg://bussola:bussola@localhost:5432/bussola"


settings = Settings()
