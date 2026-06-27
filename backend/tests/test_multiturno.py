from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from agent.deps import Dependencias
from agent.grafo import construir_grafo
from agent.llm import Plano
from agent.tools.run_sql import ResultadoSQL


class FakeLLM:
    """Registra como `condensar` foi chamada e devolve uma reescrita determinística."""

    def __init__(self, plano: Plano) -> None:
        self._plano = plano
        self.condensar_chamado_com: list[tuple[str, str]] = []

    async def condensar(self, pergunta: str, contexto_anterior: str) -> str:
        self.condensar_chamado_com.append((pergunta, contexto_anterior))
        return f"{pergunta} [contexto: {contexto_anterior}]"

    async def planejar(self, pergunta: str) -> Plano:
        return self._plano

    async def diagnosticar(self, **kwargs: Any) -> str:
        return "diagnóstico"

    async def recomendar(self, *, pergunta: str, prescricao: str, dados: str) -> str:
        return f"rec: {prescricao[:20]}"


def _exec_fraco() -> Any:
    async def _exec(sql: str) -> ResultadoSQL:
        linhas: list[dict[str, Any]]
        if "valor_meta" in sql:
            linhas = [{"valor_meta": 0.9}]
        elif "extract(year" in sql:
            linhas = [{"ano": 2025, "valor": 0.6}]
        else:
            linhas = [{"mes": "2026-01", "valor": 0.4}]
        return ResultadoSQL(colunas=["mes", "valor"], linhas=linhas, sql_executado=sql)

    return _exec


def _hit(fonte: str) -> Any:
    return SimpleNamespace(
        score=0.7, payload={"fonte": fonte, "document": "doc", "resultado": "positivo"}
    )


class FakeQdrant:
    def __init__(self, prescricoes: list[Any]) -> None:
        self._presc = prescricoes

    def query_points(self, collection_name: str, query: Any, query_filter: Any, limit: int) -> Any:
        return SimpleNamespace(points=self._presc if collection_name == "prescricao" else [])


async def _embedder(_t: str) -> list[float]:
    return [0.1]


def _deps(llm: FakeLLM, prescricoes: list[Any]) -> Dependencias:
    return Dependencias(
        llm=llm,
        executar_sql=_exec_fraco(),
        qdrant=FakeQdrant(prescricoes),
        embedder=_embedder,
        hoje=date(2026, 6, 16),
    )


async def test_primeiro_turno_nao_condensa() -> None:
    """Sem histórico, a pergunta é usada como está (condensar não chama o LLM)."""
    llm = FakeLLM(Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"}))
    grafo = construir_grafo(_deps(llm, [_hit("minio://p/sul.md")]), InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    estado = await grafo.ainvoke({"pergunta": "Como melhorar a recompra no Sul?"}, cfg)
    assert llm.condensar_chamado_com == []
    assert estado["pergunta_resolvida"] == "Como melhorar a recompra no Sul?"


async def test_followup_condensa_usando_o_turno_anterior() -> None:
    """'e no Sudeste?' é reescrito herdando o KPI/dimensão do turno anterior (mesmo thread)."""
    llm = FakeLLM(Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"}))
    grafo = construir_grafo(_deps(llm, [_hit("minio://p/sul.md")]), InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}

    await grafo.ainvoke({"pergunta": "Como melhorar a recompra no Sul?"}, cfg)
    estado2 = await grafo.ainvoke({"pergunta": "e no Sudeste?"}, cfg)

    assert len(llm.condensar_chamado_com) == 1
    pergunta, contexto = llm.condensar_chamado_com[0]
    assert pergunta == "e no Sudeste?"
    assert "taxa_recompra" in contexto  # herdou o KPI do turno 1
    assert "e no Sudeste?" in estado2["pergunta_resolvida"]


async def test_threads_isolados() -> None:
    """thread_id diferente = conversa separada: o follow-up de tB não vê o histórico de tA."""
    llm = FakeLLM(Plano(kpi_alvo="faturamento", dimensao={"regiao": "Sul"}))
    grafo = construir_grafo(_deps(llm, [_hit("minio://p/x.md")]), InMemorySaver())

    await grafo.ainvoke({"pergunta": "p1"}, {"configurable": {"thread_id": "tA"}})
    estado_b = await grafo.ainvoke({"pergunta": "p2"}, {"configurable": {"thread_id": "tB"}})
    assert estado_b["pergunta_resolvida"] == "p2"  # tB é novo: condensar não foi chamado
    assert len(estado_b.get("historico", [])) == 1  # só o próprio turno


async def test_nao_repete_recomendacao_ja_dada_na_thread() -> None:
    """Fonte recomendada no turno 1 não reaparece no turno 2 da mesma thread."""
    llm = FakeLLM(Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"}))
    presc = [_hit("minio://p/frete.md"), _hit("minio://p/brinde.md")]
    grafo = construir_grafo(_deps(llm, presc), InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}

    estado1 = await grafo.ainvoke({"pergunta": "Como melhorar a recompra no Sul?"}, cfg)
    fontes1 = {r["fonte"] for r in estado1["recomendacoes"]}
    assert fontes1 == {"minio://p/frete.md", "minio://p/brinde.md"}

    estado2 = await grafo.ainvoke({"pergunta": "e agora?"}, cfg)
    assert estado2["recomendacoes"] == []  # já foram dadas no turno 1 -> não repete


async def test_fontes_ja_recomendadas_no_input_sao_puladas() -> None:
    """O service injeta fontes já dadas (do harness durável); o relatório as ignora."""
    llm = FakeLLM(Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"}))
    grafo = construir_grafo(_deps(llm, [_hit("minio://p/frete.md")]), InMemorySaver())
    estado = await grafo.ainvoke(
        {
            "pergunta": "Como melhorar a recompra no Sul?",
            "fontes_ja_recomendadas": ["minio://p/frete.md"],
        },
        {"configurable": {"thread_id": "t1"}},
    )
    assert estado["recomendacoes"] == []  # a única prescrição já tinha sido dada
