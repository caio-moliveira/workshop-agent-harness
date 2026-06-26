from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import criar_engine
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cria o engine no startup e o descarta no shutdown — ciclo de vida explícito."""
    settings = get_settings()
    app.state.engine = criar_engine(settings.database_url)
    try:
        yield
    finally:
        await app.state.engine.dispose()


def criar_app() -> FastAPI:
    """Factory da aplicação FastAPI — facilita testar com app isolado."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health.router)
    return app


app = criar_app()
