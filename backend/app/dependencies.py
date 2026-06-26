from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine


def get_engine(request: Request) -> AsyncEngine:
    """Engine async guardado no estado da aplicação (injetável e sobreponível em teste)."""
    engine: AsyncEngine = request.app.state.engine
    return engine
