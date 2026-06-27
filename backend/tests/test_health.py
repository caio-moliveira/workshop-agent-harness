from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.dependencies import get_engine
from app.main import criar_app


@pytest.fixture
async def engine_sqlite() -> AsyncIterator[AsyncEngine]:
    """Banco em memória (SQLite async) — teste offline e determinístico, sem Postgres real."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    yield engine
    await engine.dispose()


async def test_health_responde_ok_com_banco_no_ar(engine_sqlite: AsyncEngine) -> None:
    """Com o banco respondendo, /health retorna 200 e confirma o hop ao banco."""
    app = criar_app()
    app.dependency_overrides[get_engine] = lambda: engine_sqlite

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resposta = await client.get("/health")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["banco"] == "ok"


async def test_health_degrada_para_503_quando_banco_cai(
    engine_sqlite: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Banco indisponível: /health responde 503 com status degradado (readiness correto)."""

    async def _falha_ao_pingar(_engine: AsyncEngine) -> bool:
        raise SQLAlchemyError("falha de conexão simulada")

    monkeypatch.setattr("app.services.health.verificar_conexao", _falha_ao_pingar)

    app = criar_app()
    app.dependency_overrides[get_engine] = lambda: engine_sqlite

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resposta = await client.get("/health")

    assert resposta.status_code == 503
    corpo = resposta.json()
    assert corpo["status"] == "degraded"
    assert corpo["banco"] == "erro"
