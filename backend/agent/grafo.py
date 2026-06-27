"""O grafo determinístico do agente: `planejar → perna_quantitativa → enriquecer → relatorio`.

Topologia FIXA (regra `agente.md`): o roteamento entre nós é código, não decisão de LLM
solta. O LLM decide só DENTRO de um nó (planejar escolhe KPI/dimensão; relatorio redige).
Os nós fecham sobre `Dependencias` (injeção testável) e emitem eventos incrementais via
`get_stream_writer()` — o relatório não é bufferizado inteiro antes de responder.
"""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from agent.deps import Dependencias
from agent.eventos import evento
from agent.llm import Plano
from agent.periodo import resolver_janelas
from agent.sql_templates import montar_consultas
from agent.state import EstadoAgente, Recomendacao
from agent.tools.search import buscar_enriquecimento


def _formatar_dados(dados: dict[str, list[dict[str, Any]]]) -> str:
    """Renderiza os resultsets nomeados em texto compacto para o LLM e o relatório."""
    linhas = []
    for nome, linhas_q in dados.items():
        linhas.append(f"[{nome}]")
        for r in linhas_q:
            linhas.append("  " + ", ".join(f"{k}={v}" for k, v in r.items()))
        if not linhas_q:
            linhas.append("  (sem linhas)")
    return "\n".join(linhas)


# Retorno `Any`: o grafo compilado do LangGraph (CompiledStateGraph) tem tipo genérico
# difícil de anotar de forma útil; o contrato real é só `.astream(...)` / `.ainvoke(...)`.
def construir_grafo(deps: Dependencias) -> Any:
    """Compila o grafo com as dependências injetadas. Retorna o grafo executável."""

    async def planejar(state: EstadoAgente) -> dict[str, Any]:
        """Resolve o período-alvo (mês+1, determinístico) e escolhe KPI/dimensão (LLM)."""
        writer = get_stream_writer()
        janelas = resolver_janelas(deps.hoje)
        plano: Plano = await deps.llm.planejar(state["pergunta"])
        premissas = {
            "periodo_alvo": janelas.periodo_alvo,
            "kpi_alvo": plano.kpi_alvo,
            "dimensao": plano.dimensao,
            "nota": (
                f"Período-alvo assumido: {janelas.periodo_alvo} (mês de referência + 1). "
                f"Tendência: últimos 6 meses; sazonal: {janelas.anos_sazonais}. "
                f"KPI/recorte: {plano.kpi_alvo} {plano.dimensao or '(agregado)'}."
            ),
        }
        writer(evento("premissas", **premissas))
        return {
            "periodo_alvo": janelas.periodo_alvo,
            "kpi_alvo": plano.kpi_alvo,
            "dimensao": plano.dimensao,
            "premissas": premissas,
        }

    async def perna_quantitativa(state: EstadoAgente) -> dict[str, Any]:
        """Mede tendência/sazonal via run_sql (templates determinísticos, papel RO)."""
        writer = get_stream_writer()
        janelas = resolver_janelas(deps.hoje)
        consultas = montar_consultas(state["kpi_alvo"], state.get("dimensao", {}), janelas)
        dados: dict[str, list[dict[str, Any]]] = {}
        sqls: list[str] = []
        for nome, sql in consultas.items():
            res = await deps.executar_sql(sql)
            dados[nome] = res.linhas
            sqls.append(res.sql_executado)
            writer(evento("sql", nome=nome, sql=res.sql_executado))
        texto = _formatar_dados(dados)
        writer(evento("dados", dados=dados))
        return {"dados": dados, "dados_texto": texto, "sql_executado": sqls}

    async def enriquecer(state: EstadoAgente) -> dict[str, Any]:
        """Recupera diagnóstico + prescrição (filtrados por kpi_alvo + dimensão — ADR 0002)."""
        writer = get_stream_writer()
        dimensao = state.get("dimensao", {})
        kpi = state["kpi_alvo"]
        pergunta = state["pergunta"]
        if not dimensao:
            # Sem dimensão não há recorte de negócio para enriquecer.
            writer(evento("fontes", fontes=[]))
            return {"diagnostico_hits": [], "prescricao_hits": [], "fontes": []}
        diag = await buscar_enriquecimento(
            deps.qdrant,
            deps.embedder,
            colecao="diagnostico",
            query=pergunta,
            kpi_alvo=kpi,
            dimensao=dimensao,
        )
        presc = await buscar_enriquecimento(
            deps.qdrant,
            deps.embedder,
            colecao="prescricao",
            query=pergunta,
            kpi_alvo=kpi,
            dimensao=dimensao,
        )
        fontes = [t.fonte for t in diag] + [t.fonte for t in presc]
        writer(evento("fontes", fontes=fontes))
        return {"diagnostico_hits": diag, "prescricao_hits": presc, "fontes": fontes}

    async def relatorio(state: EstadoAgente) -> dict[str, Any]:
        """Redige diagnóstico + recomendações. GROUNDING: 1 recomendação por fonte de prescrição."""
        writer = get_stream_writer()
        pergunta = state["pergunta"]
        dados_texto = state.get("dados_texto", "")
        diag_docs = "\n".join(t.document for t in state.get("diagnostico_hits", []))

        diagnostico_texto = await deps.llm.diagnosticar(
            pergunta=pergunta,
            periodo_alvo=state["periodo_alvo"],
            dados=dados_texto,
            diagnosticos=diag_docs,
        )
        writer(evento("diagnostico", texto=diagnostico_texto))

        # Grounding estrutural: itera sobre as prescrições recuperadas. Sem fonte rastreável,
        # não há recomendação (o LLM nunca inventa prescrição fora de um doc com fonte).
        recomendacoes: list[Recomendacao] = []
        for hit in state.get("prescricao_hits", []):
            if not hit.fonte or hit.fonte == "?":
                continue
            texto = await deps.llm.recomendar(
                pergunta=pergunta, prescricao=hit.document, dados=dados_texto
            )
            rec: Recomendacao = {
                "texto": texto,
                "fonte": hit.fonte,
                "resultado": str(hit.payload.get("resultado", "")),
            }
            recomendacoes.append(rec)
            writer(evento("recomendacao", **rec))

        relatorio_md = _montar_relatorio(
            premissas=state.get("premissas", {}),
            diagnostico=diagnostico_texto,
            recomendacoes=recomendacoes,
        )
        writer(evento("fim", fontes=state.get("fontes", [])))
        return {
            "diagnostico_texto": diagnostico_texto,
            "recomendacoes": recomendacoes,
            "relatorio": relatorio_md,
        }

    grafo = (
        StateGraph(EstadoAgente)
        .add_node("planejar", planejar)
        .add_node("perna_quantitativa", perna_quantitativa)
        .add_node("enriquecer", enriquecer)
        .add_node("relatorio", relatorio)
        .add_edge(START, "planejar")
        .add_edge("planejar", "perna_quantitativa")
        .add_edge("perna_quantitativa", "enriquecer")
        .add_edge("enriquecer", "relatorio")
        .add_edge("relatorio", END)
        .compile()
    )
    return grafo


def _montar_relatorio(
    *, premissas: dict[str, Any], diagnostico: str, recomendacoes: list[Recomendacao]
) -> str:
    """Monta o markdown final: premissas no topo, diagnóstico, recomendações com fonte."""
    partes = ["## Premissas", premissas.get("nota", ""), "", "## Diagnóstico", diagnostico, ""]
    partes.append("## Recomendações")
    if recomendacoes:
        for i, rec in enumerate(recomendacoes, 1):
            partes.append(
                f"{i}. {rec['texto']}  \n   _Fonte:_ `{rec['fonte']}` "
                f"(resultado: {rec['resultado']})"
            )
    else:
        partes.append(
            "_Sem prescrição com fonte rastreável para este caso — nada a recomendar "
            "sem inventar (grounding)._"
        )
    return "\n".join(partes)
