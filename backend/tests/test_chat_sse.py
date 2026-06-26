from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from decimal import Decimal

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


async def _executor(_sql: str) -> ResultadoSQL:
    return ResultadoSQL(
        colunas=["mes", "valor"], linhas=[{"mes": "2026-01", "valor": 0.61}], sql_executado=_sql
    )


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
    # o service usa RUNS (schema harness); aqui injetamos a tabela sqlite monkeypatching o default
    yield app, eng, tabela
    await eng.dispose()


async def test_chat_responde_sse_incremental_e_persiste(
    app_e_engine: tuple[Any, AsyncEngine, sa.Table], monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /chat: content-type SSE, eventos incrementais e run persistido com fontes."""
    app, eng, tabela = app_e_engine
    # o serviço grava em RUNS (schema harness) — redireciona p/ a tabela sqlite do teste
    import app.services.chat as chat_svc

    monkeypatch.setattr(chat_svc, "RUNS", tabela)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"pergunta": "Como melhorar a recompra no Sul?"}
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            corpo = ""
            async for pedaco in resp.aiter_text():
                corpo += pedaco

    # eventos incrementais presentes, na ordem esperada
    assert "event: premissas" in corpo
    assert "event: sql" in corpo
    assert "event: fontes" in corpo
    assert "event: fim" in corpo
    assert "event: run" in corpo
    assert "2024-08-sul-frete" in corpo

    # run persistido no harness (tabela de teste)
    async with eng.connect() as conn:
        n = (await conn.execute(sa.select(sa.func.count()).select_from(tabela))).scalar_one()
    assert n == 1


async def test_chat_falha_emite_evento_erro_e_persiste_run(
    app_e_engine: tuple[Any, AsyncEngine, sa.Table], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se um nó lança, o cliente recebe evento `erro` e o run é gravado mesmo assim."""
    app, eng, tabela = app_e_engine
    import app.services.chat as chat_svc

    monkeypatch.setattr(chat_svc, "RUNS", tabela)

    async def _planejar_quebra(_pergunta: str) -> Plano:
        raise ValueError("falha simulada no planejar")

    # sobrepõe o LLM para falhar no primeiro nó
    deps = app.dependency_overrides[get_deps]()
    monkeypatch.setattr(deps.llm, "planejar", _planejar_quebra)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("POST", "/chat", json={"pergunta": "x"}) as resp:
            assert resp.status_code == 200
            corpo = "".join([p async for p in resp.aiter_text()])

    assert "event: erro" in corpo
    assert "event: run" in corpo  # run ainda é emitido/persistido
    async with eng.connect() as conn:
        n = (await conn.execute(sa.select(sa.func.count()).select_from(tabela))).scalar_one()
    assert n == 1
