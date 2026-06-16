"""Endpoint POST /chat (issues #19, #21, #23): pergunta NL -> grafo -> relatorio.

Responde por streaming SSE (`text/event-stream`): eventos de progresso do grafo e,
ao final, o relatorio fundamentado com fontes citadas (estruturadas), recomendacoes
amarradas a fontes e as chaves dos artefatos persistidos no MinIO. A orquestracao
vive em `services/chat_service.py`; este router so adapta para HTTP (rota fina).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import chat_service

router = APIRouter()


class ChatRequest(BaseModel):
    pergunta: str
    sessao_id: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    # Preparo (sessao + condense + roteador + run) fora do gerador: falha de DB/LLM
    # vira erro HTTP antes de o stream comecar.
    preparo = await chat_service.iniciar(req.pergunta, req.sessao_id)
    return StreamingResponse(
        chat_service.stream(preparo),
        media_type="text/event-stream",
        headers={
            "X-Run-Id": preparo.run_id,
            "X-Sessao-Id": preparo.sessao_id,
            "Cache-Control": "no-cache",
        },
    )
