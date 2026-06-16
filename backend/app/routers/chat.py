"""Endpoint POST /chat (issues #19, #21): pergunta NL -> grafo -> relatorio fundamentado.

Grava o run no schema `harness` (runs + tool_calls + fontes_recuperadas) e devolve o
relatorio com as fontes citadas e as recomendacoes (cada uma amarrada a uma fonte).
Streaming e persistencia no MinIO chegam na #23.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from agent.graph import run_chat
from agent.tracing import get_langfuse_callbacks
from harness import repo

router = APIRouter()


class ChatRequest(BaseModel):
    pergunta: str
    sessao_id: str | None = None


class ChatResponse(BaseModel):
    run_id: str
    periodo: str
    relatorio: str
    achados: list[dict[str, Any]]
    fontes: list[dict[str, Any]]
    recomendacoes: list[dict[str, Any]]
    sql_executado: list[str]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    run_id = await repo.criar_run(req.pergunta, req.sessao_id)
    try:
        state = await run_chat(req.pergunta, callbacks=get_langfuse_callbacks(run_id))
        sql_log = state.get("sql_log", [])
        for ordem, sql in enumerate(sql_log):
            await repo.registrar_tool_call(run_id, ordem, "run_sql", sql_text=sql)
        for fonte in state.get("fontes", []):
            await repo.registrar_fonte(
                run_id, fonte.get("colecao", ""), fonte=fonte.get("fonte"), payload=fonte
            )
        await repo.finalizar_run(run_id, state.get("relatorio", ""))
    except Exception:
        await repo.finalizar_run(run_id, "", status="erro")
        raise
    return ChatResponse(
        run_id=run_id,
        periodo=state.get("periodo", ""),
        relatorio=state.get("relatorio", ""),
        achados=state.get("achados", []),
        fontes=state.get("fontes", []),
        recomendacoes=state.get("recomendacoes", []),
        sql_executado=sql_log,
    )
