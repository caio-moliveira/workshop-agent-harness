from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Configuração da aplicação — única fonte de verdade (lê do ambiente / .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "workshop-api"

    # Conexão ADMIN (RW) da app/migrations. No compose vem como DATABASE_URL p/ host=postgres:5432
    # (rede interna). Default é só fallback p/ rodar no host — Postgres publicado na 5433
    # (POSTGRES_PORT do .env do workshop). O agente NUNCA usa esta conexão (invariante #2/#3).
    database_url: str = "postgresql+asyncpg://workshop:workshop@localhost:5433/workshop"

    # Papel SOMENTE-LEITURA do agente (run_sql) — criado pela migration. A URL RO é derivada da
    # admin trocando só usuário/senha. Sem default na senha: exigir no ambiente evita papel de
    # login com senha conhecida.
    agente_ro_user: str = "agente_ro"
    agente_ro_password: str | None = None

    # Guardrails determinísticos de run_sql aplicados no banco.
    statement_timeout_ms: int = 5000
    max_rows: int = 1000

    # Stores auxiliares.
    qdrant_url: str = "http://localhost:6333"
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "corpus"
    # Bucket dos artefatos gerados (relatórios/SQL) — separado do corpus de leitura.
    minio_bucket_relatorios: str = "relatorios"

    # Embeddings da query (OpenAI) em runtime — só para embeddar a pergunta.
    openai_api_key: str | None = None
    embed_model: str = "text-embedding-3-large"
    embed_dim: int = 3072

    # Modelos do agente (provider OpenAI). Não hardcode model id nos nós — leia daqui.
    llm_model_forte: str = "gpt-4o"
    llm_model_rapido: str = "gpt-4o-mini"

    # Âncora temporal: "hoje" injetável (determinismo dos evals). "próximo mês" = +1 daqui.
    hoje_ancora: date = date(2026, 6, 16)

    @property
    def agente_ro_url(self) -> str:
        """DSN somente-leitura: a admin com usuário/senha trocados pelo papel RO."""
        if not self.agente_ro_password:
            raise RuntimeError(
                "AGENTE_RO_PASSWORD ausente — defina no ambiente/.env antes de usar o papel RO."
            )
        url = make_url(self.database_url).set(
            username=self.agente_ro_user,
            password=self.agente_ro_password,
        )
        return url.render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    """Instância única e cacheada das configurações (evita reler o ambiente a cada chamada)."""
    return Settings()
