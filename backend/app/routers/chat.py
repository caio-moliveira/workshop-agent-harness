"""Router `/chat` — fino: valida entrada, delega ao serviço, devolve SSE.

Sem lógica de domínio aqui (regra `backend.md`): a orquestração vive em `services/chat.py`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from app.dependencies import get_artefatos, get_engine, get_grafo
from app.services.chat import gerar_eventos_sse
from harness.artefatos import Artefatos

router = APIRouter(tags=["chat"])


class PerguntaIn(BaseModel):
    """Corpo do POST /chat: a pergunta + o thread_id (opcional) para conversa multi-turno."""

    pergunta: str = Field(min_length=1)
    # UUID validado no boundary: thread_id inválido vira 422, não estoura no gravar_run
    # (a coluna harness.runs.thread_id é uuid). O front ecoa o UUID devolvido no evento `run`.
    thread_id: UUID | None = None


@router.post("/chat")
async def chat(
    corpo: PerguntaIn,
    grafo: Any = Depends(get_grafo),
    engine: AsyncEngine = Depends(get_engine),
    artefatos: Artefatos = Depends(get_artefatos),
) -> StreamingResponse:
    """Responde em streaming SSE: premissas → sql → fontes → diagnóstico → recomendações → run.

    `thread_id` ausente abre uma conversa nova; presente continua a anterior (multi-turno).
    """
    gerador = gerar_eventos_sse(
        corpo.pergunta,
        grafo=grafo,
        engine_admin=engine,
        artefatos=artefatos,
        thread_id=str(corpo.thread_id) if corpo.thread_id is not None else None,
    )
    return StreamingResponse(gerador, media_type="text/event-stream")
