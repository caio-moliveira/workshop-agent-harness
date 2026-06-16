"""Grafo LangGraph deterministico do agente (issue #19).

Arestas fixas `planejar -> perna_quantitativa -> relatorio`. O LLM decide so dentro
de nos (entender a pergunta, redigir a narrativa). A leitura quantitativa usa a tool
`run_sql` (read-only, com guardrails). Fatia minima: foca em `faturamento` por regiao;
janelas temporais (#20) e enriquecimento por KPI fraco (#21) chegam depois.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph

from agent.llm import get_chat_model
from agent.state import ChatState
from agent.tools.run_sql import run_sql

_KPIS_VALIDOS = ("faturamento", "ticket_medio", "taxa_recompra", "taxa_conversao")

_PROMPT_PLANEJAR = (
    "Voce ajuda um gestor comercial. A partir da pergunta, devolva SOMENTE um JSON "
    '{{"kpis": [...]}} com os KPIs de interesse, escolhidos entre '
    "faturamento, ticket_medio, taxa_recompra, taxa_conversao. Se a pergunta for vaga, "
    'use ["faturamento"].\n\nPergunta: {pergunta}'
)

_PROMPT_RELATORIO = (
    "Voce e um analista de vendas. Escreva um relatorio curto em portugues sobre o "
    "periodo {periodo}, respondendo a pergunta do gestor. Liste os KPIs abaixo da meta "
    "(achados) e, para cada um, o quanto ficou abaixo. Se nao houver achados, diga que "
    "tudo esta dentro da meta. Nao invente numeros alem dos fornecidos.\n\n"
    "Pergunta: {pergunta}\nAchados (JSON): {achados}"
)


def _text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = [b.get("text", "") if isinstance(b, dict) else str(b) for b in content]
        return "".join(partes)
    return str(content)


def _parse_kpis(texto: str) -> list[str]:
    try:
        inicio, fim = texto.index("{"), texto.rindex("}") + 1
        dados = json.loads(texto[inicio:fim])
        kpis = [k for k in dados.get("kpis", []) if k in _KPIS_VALIDOS]
        if kpis:
            return kpis
    except (ValueError, json.JSONDecodeError):
        pass
    return ["faturamento"]


def _proximo_mes(ano: int, mes: int) -> str:
    return f"{ano + 1:04d}-01-01" if mes == 12 else f"{ano:04d}-{mes + 1:02d}-01"


async def _no_planejar(state: ChatState) -> dict[str, Any]:
    periodo_res = await run_sql(
        "SELECT ano, mes FROM negocio.metas ORDER BY ano DESC, mes DESC LIMIT 1"
    )
    if periodo_res.rows:
        ano, mes = int(periodo_res.rows[0][0]), int(periodo_res.rows[0][1])
        periodo = f"{ano:04d}-{mes:02d}"
    else:
        periodo = "?"
    msg = await get_chat_model("forte").ainvoke(
        _PROMPT_PLANEJAR.format(pergunta=state["pergunta"])
    )
    return {"periodo": periodo, "kpis_foco": _parse_kpis(_text(msg)), "sql_log": [periodo_res.sql]}


async def _no_perna_quantitativa(state: ChatState) -> dict[str, Any]:
    periodo = state.get("periodo", "?")
    if len(periodo) != 7 or "-" not in periodo:
        return {"achados": [], "sql_log": []}
    ano, mes = int(periodo[:4]), int(periodo[5:7])
    inicio, fim = f"{periodo}-01", _proximo_mes(ano, mes)

    achados: list[dict[str, Any]] = []
    sql_log: list[str] = []
    if "faturamento" in state.get("kpis_foco", ["faturamento"]):
        realizado = await run_sql(
            "SELECT r.nome AS regiao, COALESCE(SUM(p.valor_total), 0) AS realizado "
            "FROM negocio.regioes r "
            "LEFT JOIN negocio.pedidos p ON p.regiao_id = r.id AND p.status = 'pago' "
            f"AND p.data_pedido >= '{inicio}' AND p.data_pedido < '{fim}' "
            "GROUP BY r.nome ORDER BY r.nome"
        )
        metas = await run_sql(
            "SELECT r.nome AS regiao, m.valor_meta FROM negocio.metas m "
            "JOIN negocio.regioes r ON r.id = m.regiao_id "
            f"WHERE m.kpi = 'faturamento' AND m.ano = {ano} AND m.mes = {mes} "
            "AND m.regiao_id IS NOT NULL"
        )
        sql_log += [realizado.sql, metas.sql]
        meta_por_regiao = {row[0]: float(row[1]) for row in metas.rows}
        for regiao, valor in ((row[0], float(row[1])) for row in realizado.rows):
            meta = meta_por_regiao.get(regiao)
            if meta and meta > 0 and valor < meta:
                achados.append(
                    {
                        "kpi": "faturamento",
                        "dimensao": f"regiao={regiao}",
                        "realizado": valor,
                        "meta": meta,
                        "gap_pct": round((valor - meta) / meta * 100, 1),
                    }
                )
    return {"achados": achados, "sql_log": sql_log}


async def _no_relatorio(state: ChatState) -> dict[str, Any]:
    msg = await get_chat_model("forte").ainvoke(
        _PROMPT_RELATORIO.format(
            pergunta=state["pergunta"],
            periodo=state.get("periodo", "?"),
            achados=json.dumps(state.get("achados", []), ensure_ascii=False),
        )
    )
    return {"relatorio": _text(msg)}


def build_graph() -> Any:
    g = StateGraph(ChatState)
    g.add_node("planejar", _no_planejar)
    g.add_node("perna_quantitativa", _no_perna_quantitativa)
    g.add_node("relatorio", _no_relatorio)
    g.add_edge(START, "planejar")
    g.add_edge("planejar", "perna_quantitativa")
    g.add_edge("perna_quantitativa", "relatorio")
    g.add_edge("relatorio", END)
    return g.compile()


GRAPH = build_graph()


async def run_chat(pergunta: str, callbacks: list[Any] | None = None) -> dict[str, Any]:
    config = {"callbacks": callbacks} if callbacks else {}
    return await GRAPH.ainvoke({"pergunta": pergunta}, config=config)
