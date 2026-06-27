from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from harness.modelo import RegistroRun, construir_tabela_runs
from harness.repo import fontes_recomendadas_da_thread, gravar_run


@pytest.fixture
async def engine_e_tabela() -> AsyncIterator[tuple[AsyncEngine, sa.Table]]:
    """SQLite com a tabela runs sem schema (portabilidade — SQLite não tem schemas)."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    md = sa.MetaData()
    tabela = construir_tabela_runs(md, schema=None)
    async with eng.begin() as conn:
        await conn.run_sync(md.create_all)
    yield eng, tabela
    await eng.dispose()


async def test_gravar_run_persiste_e_retorna_id(
    engine_e_tabela: tuple[AsyncEngine, sa.Table],
) -> None:
    """Um run é gravado com todos os campos do contrato e recuperável pelo id."""
    engine, tabela = engine_e_tabela
    registro = RegistroRun(
        id=str(uuid.uuid4()),
        pergunta="Como melhorar a recompra no Sul?",
        periodo_alvo="2026-07",
        kpi_alvo="taxa_recompra",
        dimensao={"regiao": "Sul"},
        sql_executado=["SELECT 1"],
        fontes=["minio://corpus/prescricao/2024-08-sul-frete.md"],
        relatorio="## Premissas\n...",
        artefatos={"relatorio": "minio://relatorios/run/x.md"},
    )
    run_id = await gravar_run(engine, registro, tabela=tabela)
    assert run_id == registro.id

    async with engine.connect() as conn:
        linha = (
            (await conn.execute(sa.select(tabela).where(tabela.c.id == run_id))).mappings().one()
        )
    assert linha["kpi_alvo"] == "taxa_recompra"
    assert linha["dimensao"] == {"regiao": "Sul"}
    assert linha["fontes"] == ["minio://corpus/prescricao/2024-08-sul-frete.md"]


async def test_fontes_recomendadas_da_thread_agrega_por_thread(
    engine_e_tabela: tuple[AsyncEngine, sa.Table],
) -> None:
    """Agrega as fontes dos runs de uma thread; outra thread fica isolada."""
    engine, tabela = engine_e_tabela
    base: dict[str, Any] = dict(
        periodo_alvo="2026-07",
        kpi_alvo="taxa_recompra",
        dimensao={"regiao": "Sul"},
        sql_executado=["SELECT 1"],
        relatorio="r",
        artefatos={},
    )
    t1 = "11111111-1111-1111-1111-111111111111"
    t2 = "22222222-2222-2222-2222-222222222222"
    await gravar_run(
        engine,
        RegistroRun(
            id=str(uuid.uuid4()), pergunta="p1", fontes=["minio://a.md"], thread_id=t1, **base
        ),
        tabela=tabela,
    )
    await gravar_run(
        engine,
        RegistroRun(
            id=str(uuid.uuid4()), pergunta="p2", fontes=["minio://b.md"], thread_id=t1, **base
        ),
        tabela=tabela,
    )
    await gravar_run(
        engine,
        RegistroRun(
            id=str(uuid.uuid4()), pergunta="p3", fontes=["minio://c.md"], thread_id=t2, **base
        ),
        tabela=tabela,
    )

    fontes = await fontes_recomendadas_da_thread(engine, t1, tabela=tabela)
    assert fontes == {"minio://a.md", "minio://b.md"}  # thread 2 não vaza
