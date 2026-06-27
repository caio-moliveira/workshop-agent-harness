from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from langgraph.checkpoint.memory import InMemorySaver
from minio import Minio
from openai import OpenAI
from qdrant_client import QdrantClient

from agent.deps import Dependencias, executor_run_sql
from agent.grafo import construir_grafo
from agent.llm import criar_llm
from agent.tools.embeddings import criar_embedder
from agent.tools.search import ClienteQdrant
from app.config import Settings, get_settings
from app.db import criar_engine
from app.routers import chat, health
from harness.artefatos import ArtefatosMinio


def _montar_dependencias(app: FastAPI, settings: Settings) -> None:
    """Constrói os clientes do agente uma vez no startup e os guarda em app.state."""
    app.state.engine = criar_engine(settings.database_url)  # admin (RW): harness
    app.state.ro_engine = criar_engine(settings.agente_ro_url)  # papel agente_ro: run_sql

    # Clientes externos são lazy (não validam credenciais na construção).
    openai_client = OpenAI(api_key=settings.openai_api_key or "sk-absent")
    qdrant = QdrantClient(url=settings.qdrant_url)
    minio = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )

    app.state.deps = Dependencias(
        llm=criar_llm(
            openai_client,
            modelo_forte=settings.llm_model_forte,
            modelo_rapido=settings.llm_model_rapido,
        ),
        executar_sql=executor_run_sql(
            app.state.ro_engine,
            max_rows=settings.max_rows,
            statement_timeout_ms=settings.statement_timeout_ms,
        ),
        # O QdrantClient real satisfaz o contrato mínimo ClienteQdrant (assinatura mais ampla).
        qdrant=cast(ClienteQdrant, qdrant),
        embedder=criar_embedder(openai_client, model=settings.embed_model, dim=settings.embed_dim),
        hoje=settings.hoje_ancora,
    )
    app.state.artefatos = ArtefatosMinio(minio, bucket=settings.minio_bucket_relatorios)
    # Grafo único com checkpointer em memória — lembra cada thread enquanto o processo vive
    # (durabilidade real ficaria num PostgresSaver; o não-repetir já é durável via harness).
    app.state.grafo = construir_grafo(app.state.deps, InMemorySaver())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Monta as dependências no startup e descarta os engines no shutdown."""
    _montar_dependencias(app, get_settings())
    try:
        yield
    finally:
        await app.state.engine.dispose()
        await app.state.ro_engine.dispose()


def criar_app() -> FastAPI:
    """Factory da aplicação FastAPI — facilita testar com app isolado."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(chat.router)
    return app


app = criar_app()
