from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from agent.deps import Dependencias
from agent.grafo import construir_grafo
from agent.llm import Plano
from agent.tools.run_sql import ResultadoSQL


class FakeLLM:
    """LLM determinístico: plano fixo + textos canned. Nenhuma chamada a OpenAI."""

    def __init__(self, plano: Plano) -> None:
        self._plano = plano
        self.recomendacoes_pedidas = 0

    async def planejar(self, pergunta: str) -> Plano:
        return self._plano

    async def diagnosticar(self, **kwargs: Any) -> str:
        return "A recompra no Sul caiu vs. anos anteriores — queda real, não sazonal."

    async def recomendar(self, *, pergunta: str, prescricao: str, dados: str) -> str:
        self.recomendacoes_pedidas += 1
        return f"Recomendação baseada em: {prescricao[:30]}"


def _fake_executor(linhas: list[dict[str, Any]]) -> Any:
    async def _exec(sql: str) -> ResultadoSQL:
        return ResultadoSQL(colunas=["mes", "valor"], linhas=linhas, sql_executado=sql)

    return _exec


class FakeQdrant:
    """Devolve hits canned por coleção (diagnostico/prescricao)."""

    def __init__(self, por_colecao: dict[str, list[Any]]) -> None:
        self._por_colecao = por_colecao

    def query_points(self, collection_name: str, query: Any, query_filter: Any, limit: int) -> Any:
        return SimpleNamespace(points=self._por_colecao.get(collection_name, []))


async def _embedder(_texto: str) -> list[float]:
    return [0.0, 0.1]


def _hit(fonte: str, doc: str, resultado: str = "positivo") -> Any:
    return SimpleNamespace(
        score=0.7, payload={"fonte": fonte, "document": doc, "resultado": resultado}
    )


def _deps(llm: FakeLLM, qdrant: FakeQdrant) -> Dependencias:
    return Dependencias(
        llm=llm,
        executar_sql=_fake_executor([{"mes": "2026-01", "valor": 0.477}]),
        qdrant=qdrant,
        embedder=_embedder,
        hoje=date(2026, 6, 16),
    )


async def test_n1_grafo_produz_relatorio_com_fonte_por_recomendacao() -> None:
    """N1: identifica taxa_recompra/Sul e amarra cada recomendação a uma fonte de prescrição."""
    llm = FakeLLM(Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"}))
    qdrant = FakeQdrant(
        {
            "diagnostico": [_hit("minio://corpus/diagnostico/2025-11-sul.md", "atrasos no Sul")],
            "prescricao": [
                _hit("minio://corpus/prescricao/2024-08-sul-frete.md", "frete grátis", "positivo"),
                _hit("minio://corpus/prescricao/2025-03-sul-brinde.md", "brinde genérico", "nulo"),
            ],
        }
    )
    grafo = construir_grafo(_deps(llm, qdrant))
    estado = await grafo.ainvoke({"pergunta": "Como melhorar a recompra no Sul no próximo mês?"})

    assert estado["kpi_alvo"] == "taxa_recompra"
    assert estado["dimensao"] == {"regiao": "Sul"}
    assert estado["periodo_alvo"] == "2026-07"
    assert len(estado["recomendacoes"]) == 2
    for rec in estado["recomendacoes"]:
        assert rec["fonte"].startswith("minio://corpus/prescricao/")
    assert "## Premissas" in estado["relatorio"]
    assert "minio://corpus/prescricao/2024-08-sul-frete.md" in estado["relatorio"]


async def test_grounding_sem_prescricao_nao_gera_recomendacao() -> None:
    """Sem hit de prescrição → zero recomendações; o relatório diz isso (não inventa)."""
    llm = FakeLLM(Plano(kpi_alvo="taxa_recompra", dimensao={"regiao": "Sul"}))
    qdrant = FakeQdrant({"diagnostico": [_hit("minio://x.md", "ctx")], "prescricao": []})
    grafo = construir_grafo(_deps(llm, qdrant))
    estado = await grafo.ainvoke({"pergunta": "Como melhorar a recompra no Sul?"})

    assert estado["recomendacoes"] == []
    assert llm.recomendacoes_pedidas == 0
    assert "grounding" in estado["relatorio"].lower()


async def test_stream_emite_eventos_incrementais() -> None:
    """O grafo emite eventos custom (premissas→sql→fontes→...→fim) — não bufferiza tudo."""
    llm = FakeLLM(Plano(kpi_alvo="faturamento", dimensao={"canal": "loja_fisica"}))
    qdrant = FakeQdrant(
        {"diagnostico": [], "prescricao": [_hit("minio://corpus/prescricao/p.md", "omnichannel")]}
    )
    grafo = construir_grafo(_deps(llm, qdrant))
    tipos = []
    async for chunk in grafo.astream(
        {"pergunta": "O que fazer com a loja física?"}, stream_mode="custom"
    ):
        tipos.append(chunk["tipo"])

    assert tipos[0] == "premissas"
    assert "sql" in tipos
    assert "fontes" in tipos
    assert tipos[-1] == "fim"
