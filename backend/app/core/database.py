"""Engine assíncrona e dependência de conexão.

Nesta fatia (esqueleto andante) só provamos conectividade (SELECT 1 no /health). As tabelas
e o ORM entram quando houver o que ler/gravar (issues #2/#4).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)


async def get_connection() -> AsyncIterator[AsyncConnection]:
    """Dependência FastAPI: abre uma conexão async por requisição."""
    async with engine.connect() as conn:
        yield conn
