"""Configuracao da aplicacao.

Le do ambiente via pydantic-settings; nunca hardcode segredo. No container, o
docker-compose injeta DATABASE_URL apontando para o host `postgres`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Conexao admin (RW) do app. Sobrescrita pelo ambiente (DATABASE_URL).
    database_url: str = "postgresql+asyncpg://bussola:bussola@postgres:5432/bussola"

    # Papel somente-leitura do agente (run_sql). Criado na migration 0001 (#16).
    agente_ro_user: str = "agente_ro"
    agente_ro_password: str = ""

    # Qdrant + embeddings (issue #18). Defaults locais; sobrescritos pelo ambiente.
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""
    embed_model: str = "text-embedding-3-large"
    embed_dim: int = 3072

    @property
    def agente_ro_url(self) -> str:
        """URL async com as credenciais read-only do agente, derivada da DATABASE_URL."""
        url = make_url(self.database_url).set(
            username=self.agente_ro_user,
            password=self.agente_ro_password,
        )
        return url.render_as_string(hide_password=False)


settings = Settings()
