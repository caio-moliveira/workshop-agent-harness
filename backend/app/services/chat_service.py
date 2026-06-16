"""Orquestracao do POST /chat (issues #19, #21, #23, #24).

Porta de entrada conversacional + execucao do turno:
1. Sessao: usa a `sessao_id` recebida ou cria uma nova (turnos = runs da sessao).
2. Condense-question + roteador de intencao (`agent.conversa.rotear`) sobre o historico.
3. Sub-grafo analitico (stateless) com a pergunta ja reescrita e as prescricoes ja
   recomendadas na sessao excluidas (nao repete recomendacao).
4. Persiste o turno no `harness`, grava artefatos no MinIO e transmite por SSE.

A logica fica aqui; o router so adapta para HTTP (rota fina).

Formato SSE: cada evento e `event: <tipo>\\ndata: <json>\\n\\n`. Tipos:
- `inicio`       -> {run_id, sessao_id, intencao, pergunta_reescrita}
- `progresso`    -> {no} (no do grafo concluido)
- `clarificacao` -> {run_id, sessao_id, pergunta} (roteador pediu para reformular)
- `final`        -> payload completo (relatorio, achados, fontes, recomendacoes, artefatos)
- `erro`         -> {run_id, detalhe} (contrato de erro: nunca stack trace cru)
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from agent.conversa import rotear
from agent.graph import run_chat_stream
from agent.llm import get_chat_model
from agent.tracing import get_langfuse_callbacks
from app.services import charts, storage
from harness import repo

logger = logging.getLogger(__name__)


@dataclass
class PreparoTurno:
    run_id: str
    sessao_id: str
    intencao: str
    pergunta_reescrita: str
    fontes_excluidas: list[str] = field(default_factory=list)


def _sse(tipo: str, dados: Any) -> str:
    return f"event: {tipo}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"


async def iniciar(pergunta: str, sessao_id: str | None = None) -> PreparoTurno:
    """Cria/recupera a sessao, reescreve a pergunta, roteia a intencao e abre o run.

    Fora do gerador de streaming: falhas de DB/LLM aqui viram erro HTTP normal, antes
    de a resposta de streaming comecar.
    """
    if sessao_id is None:
        sessao_id = await repo.criar_sessao()
        historico: list[dict[str, Any]] = []
        excluidas: list[str] = []  # primeira pergunta da sessao nao tem o que excluir
    else:
        historico = await repo.historico_sessao(sessao_id)
        excluidas = await repo.fontes_prescricao_da_sessao(sessao_id)

    roteamento = await rotear(pergunta, historico, get_chat_model("rapido"))
    run_id = await repo.criar_run(pergunta, sessao_id, roteamento.pergunta_reescrita)
    return PreparoTurno(
        run_id=run_id,
        sessao_id=sessao_id,
        intencao=roteamento.intencao,
        pergunta_reescrita=roteamento.pergunta_reescrita,
        fontes_excluidas=excluidas,
    )


async def stream(preparo: PreparoTurno) -> AsyncIterator[str]:
    """Gera os eventos SSE do turno ja preparado."""
    run_id, sessao_id = preparo.run_id, preparo.sessao_id
    yield _sse(
        "inicio",
        {
            "run_id": run_id,
            "sessao_id": sessao_id,
            "intencao": preparo.intencao,
            "pergunta_reescrita": preparo.pergunta_reescrita,
        },
    )

    # Roteador pediu clarificacao: nao roda o grafo nem o MinIO; devolve a pergunta.
    if preparo.intencao == "clarificacao":
        await repo.finalizar_run(run_id, preparo.pergunta_reescrita, status="clarificacao")
        yield _sse(
            "clarificacao",
            {"run_id": run_id, "sessao_id": sessao_id, "pergunta": preparo.pergunta_reescrita},
        )
        return

    estado: dict[str, Any] = {}
    try:
        async for tipo, dado in run_chat_stream(
            preparo.pergunta_reescrita,
            callbacks=get_langfuse_callbacks(run_id),
            fontes_excluidas=preparo.fontes_excluidas,
        ):
            if tipo == "progresso":
                yield _sse("progresso", {"no": dado})
            elif tipo == "final":
                estado = dado

        # Tools invocadas no run (run_sql + search) — o avaliador (#26) checa coleções +
        # filtros a partir daqui. Ordem contínua entre as duas tools.
        sql_log = estado.get("sql_log", [])
        ordem = 0
        for sql in sql_log:
            await repo.registrar_tool_call(run_id, ordem, "run_sql", sql_text=sql)
            ordem += 1
        for chamada in estado.get("search_log", []):
            await repo.registrar_tool_call(run_id, ordem, "search", args=chamada)
            ordem += 1
        for fonte in estado.get("fontes", []):
            await repo.registrar_fonte(
                run_id,
                fonte.get("colecao", ""),
                fonte=fonte.get("fonte"),
                payload=fonte,
                score=fonte.get("score"),
            )

        relatorio = estado.get("relatorio", "")
        await repo.finalizar_run(run_id, relatorio)
        # #26: saida estruturada do run (achados + recomendacoes com fonte), para o
        # avaliador julgar faithfulness/relevancy direto do harness.
        await repo.registrar_trace(
            run_id,
            "saida",
            {
                "periodo": estado.get("periodo", ""),
                "premissas": estado.get("premissas", []),
                "achados": estado.get("achados", []),
                "recomendacoes": estado.get("recomendacoes", []),
            },
        )

        grafico = charts.spec_gaps(estado.get("achados", []), estado.get("periodo", ""))
        artefatos = await storage.persistir_artefatos(run_id, relatorio, grafico)

        yield _sse(
            "final",
            {
                "run_id": run_id,
                "sessao_id": sessao_id,
                "intencao": preparo.intencao,
                "pergunta_reescrita": preparo.pergunta_reescrita,
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
        # Stream ja respondeu 200: o erro vira evento SSE estruturado, nao um 500.
        logger.exception("falha no run %s", run_id)
        await repo.finalizar_run(run_id, "", status="erro")
        yield _sse("erro", {"run_id": run_id, "detalhe": "falha ao processar a pergunta"})
