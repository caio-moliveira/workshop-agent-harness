"""Orquestracao do POST /chat (issues #19, #21, #23).

Cria o run no schema `harness`, transmite o progresso do grafo por SSE, persiste o
relatorio + grafico no MinIO e devolve o evento final estruturado (fontes citadas
inspecionaveis pelo cliente). A logica fica aqui; o router so adapta para HTTP.

Formato SSE: cada evento e `event: <tipo>\\ndata: <json>\\n\\n`. Tipos:
- `inicio`    -> {run_id}
- `progresso` -> {no} (nome do no do grafo concluido)
- `final`     -> payload completo (relatorio, achados, fontes, recomendacoes, artefatos)
- `erro`      -> {run_id, detalhe} (contrato de erro: nunca stack trace cru)
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from agent.graph import run_chat_stream
from agent.tracing import get_langfuse_callbacks
from app.services import charts, storage
from harness import repo

logger = logging.getLogger(__name__)


def _sse(tipo: str, dados: Any) -> str:
    return f"event: {tipo}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"


async def iniciar(pergunta: str, sessao_id: str | None = None) -> str:
    """Cria o run e devolve o id. Fora do gerador, para que falha de DB vire erro HTTP
    normal antes de a resposta de streaming comecar."""
    return await repo.criar_run(pergunta, sessao_id)


async def stream(run_id: str, pergunta: str) -> AsyncIterator[str]:
    """Gera os eventos SSE do run ja criado (`run_id`)."""
    yield _sse("inicio", {"run_id": run_id})
    estado: dict[str, Any] = {}
    try:
        async for tipo, dado in run_chat_stream(
            pergunta, callbacks=get_langfuse_callbacks(run_id)
        ):
            if tipo == "progresso":
                yield _sse("progresso", {"no": dado})
            elif tipo == "final":
                estado = dado

        sql_log = estado.get("sql_log", [])
        for ordem, sql in enumerate(sql_log):
            await repo.registrar_tool_call(run_id, ordem, "run_sql", sql_text=sql)
        for fonte in estado.get("fontes", []):
            await repo.registrar_fonte(
                run_id, fonte.get("colecao", ""), fonte=fonte.get("fonte"), payload=fonte
            )

        relatorio = estado.get("relatorio", "")
        await repo.finalizar_run(run_id, relatorio)

        grafico = charts.spec_gaps(estado.get("achados", []), estado.get("periodo", ""))
        artefatos = await storage.persistir_artefatos(run_id, relatorio, grafico)

        yield _sse(
            "final",
            {
                "run_id": run_id,
                "periodo": estado.get("periodo", ""),
                "premissas": estado.get("premissas", []),
                "relatorio": relatorio,
                "achados": estado.get("achados", []),
                "fontes": estado.get("fontes", []),
                "recomendacoes": estado.get("recomendacoes", []),
                "sql_executado": sql_log,
                "artefatos": artefatos,
            },
        )
    except Exception:
        # Stream ja respondeu 200: o erro vira um evento SSE estruturado, nao um 500
        # com stack trace. Marca o run como erro e encerra o stream sem propagar.
        logger.exception("falha no run %s", run_id)
        await repo.finalizar_run(run_id, "", status="erro")
        yield _sse("erro", {"run_id": run_id, "detalhe": "falha ao processar a pergunta"})
