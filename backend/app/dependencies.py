from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from harness.artefatos import Artefatos


def get_engine(request: Request) -> AsyncEngine:
    """Engine admin (RW) guardado no estado da aplicação (injetável e sobreponível em teste)."""
    engine: AsyncEngine = request.app.state.engine
    return engine


def get_grafo(request: Request) -> Any:
    """Grafo do agente, já compilado com checkpointer no lifespan (lembra cada thread)."""
    return request.app.state.grafo


def get_artefatos(request: Request) -> Artefatos:
    """Armazenador de artefatos (MinIO) — montado no lifespan."""
    artefatos: Artefatos = request.app.state.artefatos
    return artefatos
