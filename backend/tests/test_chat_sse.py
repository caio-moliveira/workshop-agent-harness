from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from agent.deps import Dependencias
from agent.llm import Plano
from agent.tools.run_sql import ResultadoSQL
from app.dependencies import get_artefatos, get_deps, get_engine
from app.main import criar_app
from app.services.chat import _sse
from harness.modelo import construir_tabela_runs


def test_sse_serializa_decimal_do_banco() -> None:
    """Valores numeric do Postgres voltam como Decimal — o SSE precisa serializá-los."""
    linha = _sse({"tipo": "dados", "dados": {"tendencia": [{"valor": Decimal("0.477")}]}})
    assert "0.477" in linha
    assert linha.startswith("event: dados")


class FakeLLM:
    async def planejar(self, pergunta: str) -> Plano:
        return Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"})

    async def diagnosticar(self, **kwargs: Any) -> str:
        return "Diagnóstico de teste."

    async def recomendar(self, **kwargs: Any) -> str:
        return "Recomendação de teste."


class FakeQdrant:
    def query_points(self, collection_name: str, query: Any, query_filter: Any, limit: int) -> Any:
        if collection_name == "prescricao":
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        score=0.7,
                        payload={
                            "fonte": "minio://corpus/prescricao/2024-08-sul-frete.md",
                            "document": "frete grátis",
                            "resultado": "positivo",
                        },
                    )
                ]
            )
        return SimpleNamespace(points=[])


async def _embedder(_t: str) -> list[float]:
    return [0.1]


async def _executor(sql: str) -> ResultadoSQL:
    # Dados que classificam o KPI como FRACO (abaixo da meta) -> dispara enriquecimento.
    linhas: list[dict[str, Any]]
    if "valor_meta" in sql:
        linhas = [{"valor_meta": 0.8}]
    elif "extract(year" in sql:
        linhas = [{"ano": 2025, "valor": 0.61}]
    else:
        linhas = [{"mes": "2026-01", "valor": 0.477}]
    return ResultadoSQL(colunas=["mes", "valor"], linhas=linhas, sql_executado=sql)


class FakeArtefatos:
    def __init__(self) -> None:
        self.gravados: dict[str, str] = {}

    async def gravar_texto(self, caminho: str, conteudo: str, *, content_type: str) -> str:
        self.gravados[caminho] = conteudo
        return f"minio://relatorios/{caminho}"


@pytest.fixture
async def app_e_engine() -> AsyncIterator[tuple[Any, AsyncEngine, sa.Table]]:
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    md = sa.MetaData()
    tabela = construir_tabela_runs(md, schema=None)
    async with eng.begin() as conn:
        await conn.run_sync(md.create_all)

    deps = Dependencias(
        llm=FakeLLM(),
        executar_sql=_executor,
        qdrant=FakeQdrant(),
        embedder=_embedder,
        hoje=date(2026, 6, 16),
    )
    artefatos = FakeArtefatos()

    app = criar_app()
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[get_engine] = lambda: eng
    app.dependency_overrides[get_artefatos] = lambda: artefatos
    yield app, eng, tabela
    await eng.dispose()


async def test_chat_responde_sse_incremental_e_persiste(
    app_e_engine: tuple[Any, AsyncEngine, sa.Table], monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /chat: content-type SSE, eventos incrementais e run persistido com fontes."""
    app, eng, tabela = app_e_engine
    import app.services.chat as chat_svc

    monkeypatch.setattr(chat_svc, "RUNS", tabela)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"pergunta": "Como melhorar a recompra no Sul?"}
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            corpo = "".join([p async for p in resp.aiter_text()])

    assert "event: premissas" in corpo
    assert "event: sql" in corpo
    assert "event: fontes" in corpo
    assert "event: fim" in corpo
    assert "event: run" in corpo
    assert "2024-08-sul-frete" in corpo

    async with eng.connect() as conn:
        n = (await conn.execute(sa.select(sa.func.count()).select_from(tabela))).scalar_one()
    assert n == 1
