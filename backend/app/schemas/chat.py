"""Contratos do endpoint de chat."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    pergunta: str = Field(min_length=1, description="Pergunta em linguagem natural.")


class ChatResponse(BaseModel):
    resposta: str
    stub: bool = True
