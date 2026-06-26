from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def criar_engine(database_url: str) -> AsyncEngine:
    """Cria o engine async do SQLAlchemy — efeito colateral de I/O isolado num único ponto."""
    return create_async_engine(database_url, pool_pre_ping=True)


async def verificar_conexao(engine: AsyncEngine) -> bool:
    """Pinga o banco (SELECT 1) — prova o hop até o Postgres no health check."""
    async with engine.connect() as conn:
        resultado = await conn.execute(text("SELECT 1"))
        return resultado.scalar_one() == 1
