"""Endpoint POST /chat (issue #19): pergunta NL -> grafo -> relatorio, run no harness.

Streaming, persistencia de graficos no MinIO e fontes qualitativas chegam nas
proximas fatias (#9/#7). Aqui o run e gravado no schema `harness` e (se configurado)
tracado no Langfuse.
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
    sql_executado: list[str]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    run_id = await repo.criar_run(req.pergunta, req.sessao_id)
    try:
        state = await run_chat(req.pergunta, callbacks=get_langfuse_callbacks(run_id))
        sql_log = state.get("sql_log", [])
        for ordem, sql in enumerate(sql_log):
            await repo.registrar_tool_call(run_id, ordem, "run_sql", sql_text=sql)
        await repo.finalizar_run(run_id, state.get("relatorio", ""))
    except Exception:
        await repo.finalizar_run(run_id, "", status="erro")
        raise
    return ChatResponse(
        run_id=run_id,
        periodo=state.get("periodo", ""),
        relatorio=state.get("relatorio", ""),
        achados=state.get("achados", []),
        sql_executado=sql_log,
    )
