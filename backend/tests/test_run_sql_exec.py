from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from agent.tools.run_sql import run_sql


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """SQLite em memória compartilhado entre conexões (StaticPool) — sem Postgres real."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.exec_driver_sql("CREATE TABLE vendas (id INTEGER, valor INTEGER)")
        await conn.exec_driver_sql(
            "INSERT INTO vendas (id, valor) VALUES (1, 10), (2, 20), (3, 30)"
        )
    yield eng
    await eng.dispose()


async def test_run_sql_executa_select_e_devolve_resultset(engine: AsyncEngine) -> None:
    res = await run_sql(
        engine, "SELECT id, valor FROM vendas ORDER BY id", max_rows=1000, statement_timeout_ms=5000
    )
    assert res.colunas == ["id", "valor"]
    assert res.linhas == [
        {"id": 1, "valor": 10},
        {"id": 2, "valor": 20},
        {"id": 3, "valor": 30},
    ]


async def test_run_sql_aplica_limit_na_execucao(engine: AsyncEngine) -> None:
    res = await run_sql(
        engine, "SELECT id FROM vendas ORDER BY id", max_rows=2, statement_timeout_ms=5000
    )
    assert len(res.linhas) == 2
    assert res.sql_executado.endswith("LIMIT 2")
