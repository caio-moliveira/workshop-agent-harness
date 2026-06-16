"""Grafo LangGraph deterministico do agente (issues #19, #20).

Arestas fixas `planejar -> perna_quantitativa -> relatorio`. O LLM decide so dentro
de nos (entender a pergunta, redigir a narrativa). A leitura quantitativa usa a tool
`run_sql` (read-only, com guardrails).

#20 — janelas temporais: `planejar` resolve o periodo-alvo = mes atual + 1 (mes atual =
ultimo mes com dados; trata virada de ano). `perna_quantitativa` separa tendencia
recente (ultimos N meses) de sazonalidade (mesmo mes-alvo nos K anos anteriores).
Foco minimo: `faturamento` por regiao. Enriquecimento por KPI fraco chega na #21.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph

from agent.llm import get_chat_model
from agent.state import ChatState
from agent.tools.run_sql import run_sql
from app.config import settings

_KPIS_VALIDOS = ("faturamento", "ticket_medio", "taxa_recompra", "taxa_conversao")

_PROMPT_PLANEJAR = (
    "Voce ajuda um gestor comercial. A partir da pergunta, devolva SOMENTE um JSON "
    '{{"kpis": [...]}} com os KPIs de interesse, escolhidos entre '
    "faturamento, ticket_medio, taxa_recompra, taxa_conversao. Se a pergunta for vaga, "
    'use ["faturamento"].\n\nPergunta: {pergunta}'
)

_PROMPT_RELATORIO = (
    "Voce e um analista de vendas. Escreva um relatorio curto em portugues para o "
    "periodo-alvo {periodo} (proximo mes). Para cada achado, contraste a tendencia "
    "recente (ultimos {meses} meses) com a sazonalidade (mesmo mes nos {anos} anos "
    "anteriores), separando queda real de variacao sazonal. Se nao houver achados, diga "
    "que tudo esta dentro da meta. Nao invente numeros alem dos fornecidos.\n\n"
    "Pergunta: {pergunta}\nAchados (JSON): {achados}"
)


def _text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
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


def _add_meses(ano: int, mes: int, delta: int) -> tuple[int, int]:
    base = ano * 12 + (mes - 1) + delta
    return base // 12, base % 12 + 1


def _gap_pct(realizado: float, meta: float) -> float | None:
    if meta and meta > 0:
        return round((realizado - meta) / meta * 100, 1)
    return None


async def _no_planejar(state: ChatState) -> dict[str, Any]:
    # Mes atual = ultimo mes com dados; periodo-alvo = mes atual + 1 (trata virada de ano).
    atual_res = await run_sql(
        "SELECT EXTRACT(YEAR FROM MAX(data_pedido))::int AS ano, "
        "EXTRACT(MONTH FROM MAX(data_pedido))::int AS mes FROM negocio.pedidos"
    )
    if atual_res.rows and atual_res.rows[0][0] is not None:
        ano_a, mes_a = int(atual_res.rows[0][0]), int(atual_res.rows[0][1])
    else:
        ano_a, mes_a = 1970, 1
    ano_t, mes_t = _add_meses(ano_a, mes_a, 1)
    msg = await get_chat_model("forte").ainvoke(_PROMPT_PLANEJAR.format(pergunta=state["pergunta"]))
    return {
        "periodo": f"{ano_t:04d}-{mes_t:02d}",
        "mes_atual": f"{ano_a:04d}-{mes_a:02d}",
        "kpis_foco": _parse_kpis(_text(msg)),
        "sql_log": [atual_res.sql],
    }


async def _no_perna_quantitativa(state: ChatState) -> dict[str, Any]:
    periodo, mes_atual = state.get("periodo", "?"), state.get("mes_atual", "?")
    if len(periodo) != 7 or len(mes_atual) != 7:
        return {"achados": [], "sql_log": []}
    ano_t, mes_t = int(periodo[:4]), int(periodo[5:7])
    ano_a, mes_a = int(mes_atual[:4]), int(mes_atual[5:7])
    if "faturamento" not in state.get("kpis_foco", ["faturamento"]):
        return {"achados": [], "sql_log": []}

    n_meses = settings.janela_tendencia_meses
    k_anos = settings.janela_sazonal_anos
    ini_ano, ini_mes = _add_meses(ano_a, mes_a, -(n_meses - 1))
    fim_excl = _add_meses(ano_a, mes_a, 1)  # exclusivo
    anos_sazonais = [ano_t - i for i in range(1, k_anos + 1)]
    anos_in = ", ".join(str(a) for a in anos_sazonais)

    tendencia = await run_sql(
        "WITH real AS ("
        "  SELECT p.regiao_id, SUM(p.valor_total) AS v FROM negocio.pedidos p "
        "  WHERE p.status = 'pago' "
        f"  AND p.data_pedido >= '{ini_ano:04d}-{ini_mes:02d}-01' "
        f"  AND p.data_pedido < '{fim_excl[0]:04d}-{fim_excl[1]:02d}-01' "
        "  GROUP BY p.regiao_id"
        "), meta AS ("
        "  SELECT regiao_id, SUM(valor_meta) AS m FROM negocio.metas "
        "  WHERE kpi = 'faturamento' AND regiao_id IS NOT NULL "
        f"  AND (ano * 100 + mes) BETWEEN {ini_ano * 100 + ini_mes} AND {ano_a * 100 + mes_a} "
        "  GROUP BY regiao_id"
        ") SELECT r.nome, COALESCE(real.v, 0), COALESCE(meta.m, 0) FROM negocio.regioes r "
        "LEFT JOIN real ON real.regiao_id = r.id LEFT JOIN meta ON meta.regiao_id = r.id "
        "ORDER BY r.nome"
    )
    sazonal = await run_sql(
        "WITH real AS ("
        "  SELECT p.regiao_id, SUM(p.valor_total) AS v FROM negocio.pedidos p "
        f"  WHERE p.status = 'pago' AND EXTRACT(MONTH FROM p.data_pedido) = {mes_t} "
        f"  AND EXTRACT(YEAR FROM p.data_pedido) IN ({anos_in}) GROUP BY p.regiao_id"
        "), meta AS ("
        "  SELECT regiao_id, SUM(valor_meta) AS m FROM negocio.metas "
        f"  WHERE kpi = 'faturamento' AND regiao_id IS NOT NULL AND mes = {mes_t} "
        f"  AND ano IN ({anos_in}) GROUP BY regiao_id"
        ") SELECT r.nome, COALESCE(real.v, 0), COALESCE(meta.m, 0) FROM negocio.regioes r "
        "LEFT JOIN real ON real.regiao_id = r.id LEFT JOIN meta ON meta.regiao_id = r.id "
        "ORDER BY r.nome"
    )

    tend = {row[0]: _gap_pct(float(row[1]), float(row[2])) for row in tendencia.rows}
    sazo = {row[0]: _gap_pct(float(row[1]), float(row[2])) for row in sazonal.rows}
    achados: list[dict[str, Any]] = []
    for regiao in tend:
        gt, gs = tend.get(regiao), sazo.get(regiao)
        abaixo_tend = gt is not None and gt < 0
        abaixo_sazo = gs is not None and gs < 0
        if abaixo_tend or abaixo_sazo:
            achados.append(
                {
                    "kpi": "faturamento",
                    "dimensao": f"regiao={regiao}",
                    "periodo_alvo": periodo,
                    "tendencia_gap_pct": gt,
                    "sazonal_gap_pct": gs,
                    "abaixo_tendencia": abaixo_tend,
                    "abaixo_sazonal": abaixo_sazo,
                }
            )
    return {"achados": achados, "sql_log": [tendencia.sql, sazonal.sql]}


async def _no_relatorio(state: ChatState) -> dict[str, Any]:
    msg = await get_chat_model("forte").ainvoke(
        _PROMPT_RELATORIO.format(
            pergunta=state["pergunta"],
            periodo=state.get("periodo", "?"),
            meses=settings.janela_tendencia_meses,
            anos=settings.janela_sazonal_anos,
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
