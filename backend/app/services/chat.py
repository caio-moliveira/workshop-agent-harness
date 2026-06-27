"""Serviço de chat: orquestra o grafo, emite SSE incremental e persiste o run.

Stream multi-modo: `custom` carrega os eventos do agente (viram SSE na hora); `values`
entrega o estado final, usado para gravar o run (schema `harness`) e os artefatos (MinIO).
A resposta é incremental — o relatório não é bufferizado inteiro antes de começar a sair.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from harness.artefatos import Artefatos
from harness.modelo import RUNS, RegistroRun
from harness.repo import fontes_recomendadas_da_thread, gravar_run


def _json_safe(obj: Any) -> Any:
    """Converte tipos vindos do banco (Decimal, date) que o JSON padrão não serializa."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Não serializável em JSON: {type(obj).__name__}")


def _sse(payload: dict[str, Any]) -> str:
    """Formata um evento como linha SSE (`event:` + `data:` JSON)."""
    tipo = str(payload.get("tipo", "mensagem"))
    dados = json.dumps(payload, ensure_ascii=False, default=_json_safe)
    return f"event: {tipo}\ndata: {dados}\n\n"


async def gerar_eventos_sse(
    pergunta: str,
    *,
    grafo: Any,
    engine_admin: AsyncEngine,
    artefatos: Artefatos,
    thread_id: str | None = None,
    tabela: sa.Table | None = None,
) -> AsyncIterator[str]:
    """Roda o grafo (com checkpointer por thread), faz streaming e persiste run + artefatos."""
    tabela = tabela if tabela is not None else RUNS  # resolvido em runtime (testável)
    thread_id = thread_id or str(uuid.uuid4())
    # Não repetir: fontes já recomendadas nesta conversa (fonte durável = harness).
    fontes_ja = await fontes_recomendadas_da_thread(engine_admin, thread_id, tabela=tabela)
    entrada = {"pergunta": pergunta, "fontes_ja_recomendadas": sorted(fontes_ja)}
    config = {"configurable": {"thread_id": thread_id}}

    estado_final: dict[str, Any] = {}
    erro: str | None = None

    try:
        async for modo, chunk in grafo.astream(entrada, config, stream_mode=["custom", "values"]):
            if modo == "custom":
                yield _sse(chunk)
            else:  # "values": fotografia do estado; a última é o estado final
                estado_final = chunk
    except Exception as exc:  # noqa: BLE001 — traduz a falha em evento SSE, sem vazar detalhe
        erro = type(exc).__name__
        yield _sse({"tipo": "erro", "mensagem": "Falha ao gerar o relatório."})

    # Persistência acontece SEMPRE: todo run é gravado, inclusive os que falharam no grafo
    # (invariante). Limite conhecido: se o MinIO/Postgres caírem AQUI (pós-stream), a exceção
    # escapa do gerador — "sempre gravado" é best-effort frente a falha de infra do próprio
    # harness (não do grafo). Tratamento robusto (retry/fila) fica para uma fatia futura.
    run_id = str(uuid.uuid4())
    relatorio = estado_final.get("relatorio", "")
    sqls: list[str] = estado_final.get("sql_executado", [])

    artefatos_uris: dict[str, str] = {
        "relatorio": await artefatos.gravar_texto(
            f"runs/{run_id}/relatorio.md", relatorio, content_type="text/markdown"
        )
    }
    if sqls:
        artefatos_uris["sql"] = await artefatos.gravar_texto(
            f"runs/{run_id}/consultas.sql", ";\n\n".join(sqls), content_type="text/plain"
        )
    if erro is not None:
        artefatos_uris["erro"] = erro  # rastro da falha junto do run (não some)

    registro = RegistroRun(
        id=run_id,
        pergunta=pergunta,
        periodo_alvo=estado_final.get("periodo_alvo", ""),
        kpi_alvo=estado_final.get("kpi_alvo", ""),
        dimensao=estado_final.get("dimensao", {}),
        sql_executado=sqls,
        fontes=estado_final.get("fontes", []),
        relatorio=relatorio,
        artefatos=artefatos_uris,
        thread_id=thread_id,
    )
    await gravar_run(engine_admin, registro, tabela=tabela)
    yield _sse(
        {
            "tipo": "run",
            "run_id": run_id,
            "thread_id": thread_id,
            "erro": erro,
            "artefatos": artefatos_uris,
        }
    )
