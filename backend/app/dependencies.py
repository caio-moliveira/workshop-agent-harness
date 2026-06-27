from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from agent.deps import Dependencias
from harness.artefatos import Artefatos


def get_engine(request: Request) -> AsyncEngine:
    """Engine admin (RW) guardado no estado da aplicação (injetável e sobreponível em teste)."""
    engine: AsyncEngine = request.app.state.engine
    return engine


def get_deps(request: Request) -> Dependencias:
    """Dependências do agente (LLM, executor SQL RO, Qdrant, embedder) — montadas no lifespan."""
    deps: Dependencias = request.app.state.deps
    return deps


def get_artefatos(request: Request) -> Artefatos:
    """Armazenador de artefatos (MinIO) — montado no lifespan."""
    artefatos: Artefatos = request.app.state.artefatos
    return artefatos
