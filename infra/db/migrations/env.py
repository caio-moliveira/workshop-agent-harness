"""Ambiente Alembic (async). A URL vem de app.config.settings — nunca hardcoded aqui.

Migrations de INFRAESTRUTURA (papéis/privilégios) rodam com a conexão ADMIN (RW).
Promover DDL de negócio para cá é decisão SOB REVISÃO HUMANA (backend.md).
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

target_metadata = None  # sem autogenerate: migrations escritas à mão e revisadas


def _url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
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
    engine = create_async_engine(_url(), poolclass=None)
    async with engine.connect() as connection:
        await connection.run_sync(_executar)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
