"""Fixtures de teste. Seam HTTP (httpx/ASGI); a conexão de banco é trocada por sqlite em memória,
para o gate (pytest sem Postgres no ar) continuar verde."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.core.database import get_connection
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def override_get_connection() -> AsyncIterator[AsyncConnection]:
        async with test_engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_connection] = override_get_connection
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await test_engine.dispose()
