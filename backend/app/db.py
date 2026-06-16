"""Acesso ao banco (issue #15).

Apenas o suficiente para o esqueleto andante: um engine async e um ping de
conectividade (`SELECT 1`) usado pelo `/health`. As tools do agente (run_sql) e o
role read-only chegam na issue #16/#17.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Engine async singleton. Injetado como dependencia para ser sobrescrito em teste."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


async def ping_db(engine: AsyncEngine) -> None:
    """Verifica a conectividade com o banco. Levanta excecao se indisponivel."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
