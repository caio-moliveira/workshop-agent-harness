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

    async def condensar(self, pergunta: str, contexto_anterior: str) -> str:
        return pergunta

    async def planejar(self, pergunta: str) -> Plano:
        return self._plano

    async def diagnosticar(self, **kwargs: Any) -> str:
        return "A recompra no Sul caiu vs. anos anteriores — queda real, não sazonal."

    async def recomendar(self, *, pergunta: str, prescricao: str, dados: str) -> str:
        self.recomendacoes_pedidas += 1
        return f"Recomendação baseada em: {prescricao[:30]}"


def _exec_por_consulta(
    *,
    tendencia: list[dict[str, Any]],
    sazonal: list[dict[str, Any]] | None = None,
    meta: list[dict[str, Any]] | None = None,
) -> Any:
    """Executor fake que distingue tendência/sazonal/meta pelo SQL (controla o roteamento)."""

    async def _exec(sql: str) -> ResultadoSQL:
        linhas: list[dict[str, Any]]
        if "valor_meta" in sql:
            linhas = meta or []
        elif "extract(year" in sql:
            linhas = sazonal or []
        else:
            linhas = tendencia
        return ResultadoSQL(colunas=["mes", "valor"], linhas=linhas, sql_executado=sql)

    return _exec


def _exec_fraco(valor: float = 0.477) -> Any:
    """Dados que classificam o KPI como FRACO (abaixo da meta) -> dispara enriquecimento."""
    return _exec_por_consulta(
        tendencia=[{"mes": "2026-01", "valor": valor}],
        sazonal=[{"ano": 2025, "valor": valor + 0.1}],
        meta=[{"valor_meta": valor + 0.2}],
    )


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


def _deps(llm: FakeLLM, qdrant: FakeQdrant, executar: Any = None) -> Dependencias:
    return Dependencias(
        llm=llm,
        executar_sql=executar or _exec_fraco(),
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


def _exec_saudavel(valor: float = 100.0) -> Any:
    """KPI no/acima da meta -> saudável -> NÃO enriquece."""
    return _exec_por_consulta(
        tendencia=[{"mes": "2026-01", "valor": valor}],
        sazonal=[{"ano": 2025, "valor": valor - 5}],
        meta=[{"valor_meta": valor - 10}],
    )


async def test_kpi_saudavel_nao_enriquece() -> None:
    """KPI acima da meta (N4-like): roteamento NÃO dispara enriquecimento; sem recomendação."""
    llm = FakeLLM(Plano(kpi_alvo="faturamento", dimensao={"regiao": "Nordeste"}))
    qdrant = FakeQdrant(
        {"diagnostico": [_hit("minio://d.md", "x")], "prescricao": [_hit("minio://p.md", "x")]}
    )
    estado = await construir_grafo(_deps(llm, qdrant, _exec_saudavel())).ainvoke(
        {"pergunta": "Investir mais em Beleza no Nordeste?"}
    )
    assert estado["saude"]["fraco"] is False
    assert estado.get("fontes", []) == []  # enriquecer foi pulado
    assert estado["recomendacoes"] == []
    assert "saudável" in estado["relatorio"].lower()


async def test_controle_sazonal_sem_meta_nao_enriquece() -> None:
    """N6-like: sem meta e valor recente não pior que anos anteriores -> saudável."""
    llm = FakeLLM(Plano(kpi_alvo="ticket_medio", dimensao={}))
    exec_sazonal = _exec_por_consulta(
        tendencia=[{"mes": "2026-01", "valor": 250.0}],
        sazonal=[{"ano": 2025, "valor": 240.0}, {"ano": 2024, "valor": 230.0}],
        meta=[],  # sem meta cadastrada
    )
    estado = await construir_grafo(_deps(llm, FakeQdrant({}), exec_sazonal)).ainvoke(
        {"pergunta": "O ticket médio sobe no fim do ano — problema?"}
    )
    assert estado["saude"]["fraco"] is False
    assert estado["recomendacoes"] == []


async def test_pergunta_vaga_declara_premissas_sem_clarificar() -> None:
    """Pergunta resolvível por default (best-effort): relatório com premissas, sem perguntar."""
    llm = FakeLLM(Plano(kpi_alvo="faturamento", dimensao={}))
    estado = await construir_grafo(_deps(llm, FakeQdrant({}), _exec_fraco(1000.0))).ainvoke(
        {"pergunta": "Como melhorar minhas vendas?"}
    )
    assert estado.get("precisa_clarificar") is False
    assert "## Premissas" in estado["relatorio"]
    assert "Preciso de mais contexto" not in estado["relatorio"]


async def test_pergunta_irresolvivel_devolve_clarificacao() -> None:
    """Só quando NADA é resolvível: devolve uma pergunta de clarificação, sem investigar."""
    plano = Plano(
        kpi_alvo="faturamento",
        precisa_clarificar=True,
        pergunta_clarificacao="Sobre qual indicador e período?",
    )
    llm = FakeLLM(plano)
    grafo = construir_grafo(_deps(llm, FakeQdrant({})))
    tipos = []
    async for chunk in grafo.astream({"pergunta": "??"}, stream_mode="custom"):
        tipos.append(chunk["tipo"])
    estado = await grafo.ainvoke({"pergunta": "??"})

    assert "clarificacao" in tipos
    assert "sql" not in tipos  # não rodou a perna quantitativa
    assert "Preciso de mais contexto" in estado["relatorio"]
    assert llm.recomendacoes_pedidas == 0
