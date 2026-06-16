"""Lógica do chat. Nesta fatia é um stub — o agente real entra em issues posteriores."""

from __future__ import annotations

from app.schemas.chat import ChatRequest, ChatResponse


def responder(req: ChatRequest) -> ChatResponse:
    """Eco determinístico: prova o trilho HTTP sem nenhuma lógica analítica."""
    return ChatResponse(
        resposta=f"[stub] recebi: '{req.pergunta}'. Agente ainda não implementado.",
        stub=True,
    )
