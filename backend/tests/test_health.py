"""Teste do seam HTTP do /health (issue #15).

Cobre os dois caminhos exigidos pela issue: banco acessivel -> 200; banco
indisponivel -> nao-200. Usa sqlite in-memory (aiosqlite) para o caminho feliz e
substitui o ping para simular falha, sem depender de um Postgres real.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.db import get_engine
from app.main import app


async def test_health_ok() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_health_db_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def boom(_engine: AsyncEngine) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr("app.main.ping_db", boom)
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert resp.status_code == 503
    assert resp.json()["status"] == "unhealthy"
