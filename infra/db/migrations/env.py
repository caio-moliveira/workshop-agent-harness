"""Ambiente Alembic (async). A URL vem de app.config.settings — nunca hardcoded aqui.

Estas migrations são de INFRAESTRUTURA (papéis/privilégios) e rodam com a conexão
ADMIN (RW). Promover DDL de negócio para cá é decisão SOB REVISÃO HUMANA (backend.md).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sem autogenerate: as migrations são escritas à mão e revisadas.
target_metadata = None


def _url() -> str:
    """Conexão admin (RW) do projeto — a mesma que a app/seed usam."""
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Modo offline: emite o SQL sem conectar (para revisão do diff de SQL)."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _executar(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Modo online: conecta (async) e aplica as migrations."""
    engine = create_async_engine(_url(), poolclass=None)
    async with engine.connect() as connection:
        await connection.run_sync(_executar)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
