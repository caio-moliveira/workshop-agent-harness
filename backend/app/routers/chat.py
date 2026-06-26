"""Router `/chat` — fino: valida entrada, delega ao serviço, devolve SSE.

Sem lógica de domínio aqui (regra `backend.md`): a orquestração vive em `services/chat.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from agent.deps import Dependencias
from app.dependencies import get_artefatos, get_deps, get_engine
from app.services.chat import gerar_eventos_sse
from harness.artefatos import Artefatos

router = APIRouter(tags=["chat"])


class PerguntaIn(BaseModel):
    """Corpo do POST /chat: a pergunta em linguagem natural do gestor."""

    pergunta: str = Field(min_length=1)


@router.post("/chat")
async def chat(
    corpo: PerguntaIn,
    deps: Dependencias = Depends(get_deps),
    engine: AsyncEngine = Depends(get_engine),
    artefatos: Artefatos = Depends(get_artefatos),
) -> StreamingResponse:
    """Responde em streaming SSE: premissas → sql → fontes → diagnóstico → recomendações → run."""
    gerador = gerar_eventos_sse(corpo.pergunta, deps=deps, engine_admin=engine, artefatos=artefatos)
    return StreamingResponse(gerador, media_type="text/event-stream")
