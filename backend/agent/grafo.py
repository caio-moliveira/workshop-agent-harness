"""O grafo determinístico do agente.

Topologia FIXA com arestas CONDICIONAIS decididas por CÓDIGO (não pelo LLM solto):

    START → planejar → ┬→ clarificar → END            (pergunta irresolvível)
                       └→ perna_quantitativa → ┬→ enriquecer → relatorio → END   (KPI fraco)
                                               └→ relatorio → END                (KPI saudável)

O LLM decide só DENTRO de um nó (planejar escolhe KPI/dimensão; relatorio redige); o
roteamento entre nós lê o dado/estado, conforme `agente.md`. Os nós fecham sobre
`Dependencias` (injeção testável) e emitem eventos incrementais via `get_stream_writer()`.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from agent.deps import Dependencias
from agent.eventos import evento
from agent.llm import Plano
from agent.periodo import resolver_janelas
from agent.saude import avaliar_saude
from agent.sql_templates import montar_consultas
from agent.state import EstadoAgente, HitEnriquecimento, Recomendacao, TurnoHistorico
from agent.tools.search import Trecho, buscar_enriquecimento


def _para_hit(trecho: Trecho) -> HitEnriquecimento:
    """Trecho -> dict serializável (o checkpointer persiste o estado entre turnos)."""
    return {
        "fonte": trecho.fonte,
        "document": trecho.document,
        "resultado": str(trecho.payload.get("resultado", "")),
    }


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


def _pergunta_atual(state: EstadoAgente) -> str:
    """A pergunta a investigar — a versão condensada (multi-turno) ou a original."""
    return state.get("pergunta_resolvida") or state["pergunta"]


def construir_grafo(deps: Dependencias, checkpointer: BaseCheckpointSaver | None = None) -> Any:
    """Compila o grafo com as dependências injetadas. Com checkpointer, lembra o thread."""

    async def condensar(state: EstadoAgente) -> dict[str, Any]:
        """Multi-turno: reescreve um follow-up ('e no Sudeste?') como pergunta autônoma,
        herdando KPI/período/dimensão do último turno (via histórico do checkpointer)."""
        historico = state.get("historico", [])
        if not historico:
            return {"pergunta_resolvida": state["pergunta"]}
        ultimo = historico[-1]
        contexto = (
            f"pergunta anterior: {ultimo['pergunta']}; KPI: {ultimo['kpi_alvo']}; "
            f"dimensão: {ultimo['dimensao'] or '(agregado)'}"
        )
        resolvida = await deps.llm.condensar(state["pergunta"], contexto)
        return {"pergunta_resolvida": resolvida}

    async def planejar(state: EstadoAgente) -> dict[str, Any]:
        """Escolhe KPI/dimensão (LLM, best-effort) e resolve o período-alvo (mês+1)."""
        writer = get_stream_writer()
        plano: Plano = await deps.llm.planejar(_pergunta_atual(state))
        if plano.precisa_clarificar:
            # Só quando NADA é resolvível — o roteamento manda para o nó de clarificação.
            return {
                "precisa_clarificar": True,
                "clarificacao": plano.pergunta_clarificacao
                or "Pode detalhar o KPI, o período ou a região/canal de interesse?",
            }
        janelas = resolver_janelas(deps.hoje)
        premissas = {
            "periodo_alvo": janelas.periodo_alvo,
            "kpi_alvo": plano.kpi_alvo,
            "dimensao": plano.dimensao,
            "nota": (
                f"Período-alvo assumido: {janelas.periodo_alvo} (mês de referência + 1). "
                f"Tendência: últimos 6 meses; sazonal: {janelas.anos_sazonais}. "
                f"KPI/recorte assumidos: {plano.kpi_alvo} {plano.dimensao or '(agregado)'}."
            ),
        }
        writer(evento("premissas", **premissas))
        return {
            "precisa_clarificar": False,
            "periodo_alvo": janelas.periodo_alvo,
            "kpi_alvo": plano.kpi_alvo,
            "dimensao": plano.dimensao,
            "premissas": premissas,
        }

    async def clarificar(state: EstadoAgente) -> dict[str, Any]:
        """Pergunta irresolvível: devolve UMA pergunta de clarificação (best-effort esgotado)."""
        writer = get_stream_writer()
        pergunta_clar = state.get("clarificacao", "Pode detalhar sua pergunta?")
        writer(evento("clarificacao", pergunta=pergunta_clar))
        writer(evento("fim", fontes=[]))
        return {"relatorio": f"## Preciso de mais contexto\n\n{pergunta_clar}"}

    async def perna_quantitativa(state: EstadoAgente) -> dict[str, Any]:
        """Mede tendência/sazonal/meta (templates RO) e classifica a saúde do KPI (data-driven)."""
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
        saude = avaliar_saude(dados)
        saude_dict = {
            "fraco": saude.fraco,
            "motivo": saude.motivo,
            "parece_sazonal": saude.parece_sazonal,
        }
        writer(evento("saude", **saude_dict))
        return {"dados": dados, "dados_texto": texto, "sql_executado": sqls, "saude": saude_dict}

    async def enriquecer(state: EstadoAgente) -> dict[str, Any]:
        """Recupera diagnóstico + prescrição (filtrados por kpi_alvo + dimensão — ADR 0002).

        O roteamento (`rota_pos_quantitativa`) só chega aqui com KPI fraco E dimensão; por
        isso não há guarda de dimensão vazia neste nó."""
        writer = get_stream_writer()
        dimensao = state.get("dimensao", {})
        kpi = state["kpi_alvo"]
        pergunta = _pergunta_atual(state)
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
        # Converte os Trechos em dicts serializáveis — o checkpointer persiste o estado.
        diag_hits = [_para_hit(t) for t in diag]
        presc_hits = [_para_hit(t) for t in presc]
        fontes = [h["fonte"] for h in diag_hits] + [h["fonte"] for h in presc_hits]
        writer(evento("fontes", fontes=fontes))
        return {"diagnostico_hits": diag_hits, "prescricao_hits": presc_hits, "fontes": fontes}

    async def relatorio(state: EstadoAgente) -> dict[str, Any]:
        """Redige diagnóstico + recomendações. GROUNDING: 1 recomendação por fonte de prescrição."""
        writer = get_stream_writer()
        pergunta = _pergunta_atual(state)
        dados_texto = state.get("dados_texto", "")
        diag_docs = "\n".join(h["document"] for h in state.get("diagnostico_hits", []))

        diagnostico_texto = await deps.llm.diagnosticar(
            pergunta=pergunta,
            periodo_alvo=state["periodo_alvo"],
            dados=dados_texto,
            diagnosticos=diag_docs,
        )
        writer(evento("diagnostico", texto=diagnostico_texto))

        # Não repetir: fontes recomendadas em turnos anteriores (durável via harness +
        # histórico do thread) ficam fora desta rodada.
        ja_recomendadas = set(state.get("fontes_ja_recomendadas", []))
        for turno in state.get("historico", []):
            ja_recomendadas.update(turno.get("fontes", []))

        # Grounding estrutural: itera sobre as prescrições recuperadas. Sem fonte → sem
        # recomendação (o LLM nunca inventa prescrição fora de um doc com fonte rastreável).
        recomendacoes: list[Recomendacao] = []
        for hit in state.get("prescricao_hits", []):
            fonte = hit["fonte"]
            if not fonte or fonte == "?":
                continue
            if fonte in ja_recomendadas:
                continue  # já recomendada antes nesta conversa — não repete
            texto = await deps.llm.recomendar(
                pergunta=pergunta, prescricao=hit["document"], dados=dados_texto
            )
            rec: Recomendacao = {
                "texto": texto,
                "fonte": fonte,
                "resultado": hit["resultado"],
            }
            recomendacoes.append(rec)
            writer(evento("recomendacao", **rec))

        relatorio_md = _montar_relatorio(
            premissas=state.get("premissas", {}),
            diagnostico=diagnostico_texto,
            recomendacoes=recomendacoes,
            saude=state.get("saude", {}),
        )
        writer(evento("fim", fontes=state.get("fontes", [])))
        # Anexa este turno ao histórico (persistido pelo checkpointer) p/ os próximos turnos.
        turno_atual: TurnoHistorico = {
            "pergunta": pergunta,
            "kpi_alvo": state.get("kpi_alvo", ""),
            "dimensao": state.get("dimensao", {}),
            "fontes": [r["fonte"] for r in recomendacoes],
        }
        return {
            "diagnostico_texto": diagnostico_texto,
            "recomendacoes": recomendacoes,
            "relatorio": relatorio_md,
            "historico": [*state.get("historico", []), turno_atual],
        }

    def rota_pos_planejar(state: EstadoAgente) -> Literal["clarificar", "perna_quantitativa"]:
        """Pergunta irresolvível vai clarificar; caso contrário segue para a perna quantitativa."""
        return "clarificar" if state.get("precisa_clarificar") else "perna_quantitativa"

    def rota_pos_quantitativa(state: EstadoAgente) -> Literal["enriquecer", "relatorio"]:
        """Enriquece só KPI FRACO E com recorte (dimensão). Saudável/sazonal/agregado vai
        direto ao relatório — sem dimensão não há fatia de negócio para buscar fontes."""
        saude = state.get("saude", {})
        if saude.get("fraco") and state.get("dimensao"):
            return "enriquecer"
        return "relatorio"

    grafo = (
        StateGraph(EstadoAgente)
        .add_node("condensar", condensar)
        .add_node("planejar", planejar)
        .add_node("clarificar", clarificar)
        .add_node("perna_quantitativa", perna_quantitativa)
        .add_node("enriquecer", enriquecer)
        .add_node("relatorio", relatorio)
        .add_edge(START, "condensar")
        .add_edge("condensar", "planejar")
        .add_conditional_edges("planejar", rota_pos_planejar, ["clarificar", "perna_quantitativa"])
        .add_edge("clarificar", END)
        .add_conditional_edges(
            "perna_quantitativa", rota_pos_quantitativa, ["enriquecer", "relatorio"]
        )
        .add_edge("enriquecer", "relatorio")
        .add_edge("relatorio", END)
        .compile(checkpointer=checkpointer)
    )
    return grafo


def _montar_relatorio(
    *,
    premissas: dict[str, Any],
    diagnostico: str,
    recomendacoes: list[Recomendacao],
    saude: dict[str, Any],
) -> str:
    """Monta o markdown final: premissas no topo, diagnóstico, recomendações (ou nota de saúde)."""
    partes = ["## Premissas", premissas.get("nota", ""), "", "## Diagnóstico", diagnostico, ""]
    partes.append("## Recomendações")
    if recomendacoes:
        for i, rec in enumerate(recomendacoes, 1):
            partes.append(
                f"{i}. {rec['texto']}  \n   _Fonte:_ `{rec['fonte']}` "
                f"(resultado: {rec['resultado']})"
            )
    elif saude and not saude.get("fraco"):
        # KPI saudável/sazonal: é oportunidade, não problema — sem recomendação corretiva.
        partes.append(
            f"_KPI saudável ({saude.get('motivo', 'no/acima da meta')}) — é oportunidade, "
            "não deficit. Sem recomendação corretiva._"
        )
    else:
        partes.append(
            "_Sem prescrição com fonte rastreável para este caso — nada a recomendar "
            "sem inventar (grounding)._"
        )
    return "\n".join(partes)
