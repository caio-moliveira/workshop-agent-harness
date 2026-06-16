"""Testes do grafo analitico (issues #19, #20, #21) — sem DB, LLM ou Qdrant reais.

`run_sql`, `get_chat_model` e `search` sao substituidos por fakes deterministicos. Cobre:
periodo-alvo (mes+1), tendencia x sazonal, e o enriquecimento com grounding (toda
recomendacao amarrada a uma fonte).
"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import agent.graph as g
from agent.tools.run_sql import SqlResult
from agent.tools.search import SearchHit


async def test_grafo_completo_com_enriquecimento_e_grounding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_sql(sql: str, **kw: object) -> SqlResult:
        if "MAX(data_pedido)" in sql:
            return SqlResult(columns=["ano", "mes"], rows=[(2026, 6)], rowcount=1, sql=sql)
        if "EXTRACT(MONTH FROM p.data_pedido)" in sql:  # sazonal
            return SqlResult(
                columns=["regiao", "real", "meta"],
                rows=[("Sul", 90.0, 100.0), ("Sudeste", 300.0, 300.0)],
                rowcount=2,
                sql=sql,
            )
        if "BETWEEN" in sql:  # tendencia
            return SqlResult(
                columns=["regiao", "real", "meta"],
                rows=[("Sul", 100.0, 200.0), ("Sudeste", 500.0, 400.0)],
                rowcount=2,
                sql=sql,
            )
        return SqlResult(columns=[], rows=[], rowcount=0, sql=sql)

    async def fake_search(collection: str, query: str, filters: object, **kw: object):
        if collection == "diagnostico":
            return [SearchHit(fonte="minio://diag/sul.md", score=0.7, payload={"document": "atrasos"})]
        if collection == "prescricao":
            return [
                SearchHit(
                    fonte="minio://presc/frete.md",
                    score=0.6,
                    payload={"document": "frete gratis no Sul", "resultado": "positivo"},
                )
            ]
        return []

    fake_llm = FakeListChatModel(responses=['{"kpis": ["faturamento"]}', "Relatorio com fontes."])
    monkeypatch.setattr(g, "run_sql", fake_run_sql)
    monkeypatch.setattr(g, "search", fake_search)
    monkeypatch.setattr(g, "get_chat_model", lambda tier="forte": fake_llm)

    state = await g.run_chat("como melhorar minhas vendas no proximo mes?")

    assert state["periodo"] == "2026-07"
    assert any(a["dimensao"] == "regiao=Sul" for a in state["achados"])
    # Enriquecimento: fontes de diagnostico + prescricao recuperadas.
    assert any(f["colecao"] == "diagnostico" for f in state["fontes"])
    assert any(f["colecao"] == "prescricao" for f in state["fontes"])
    # Grounding: toda recomendacao tem uma fonte rastreavel.
    assert state["recomendacoes"]
    assert all(r.get("fonte") for r in state["recomendacoes"])
    assert state["recomendacoes"][0]["resultado"] == "positivo"


def test_add_meses_trata_virada_de_ano() -> None:
    assert g._add_meses(2026, 6, 1) == (2026, 7)
    assert g._add_meses(2026, 12, 1) == (2027, 1)
    assert g._add_meses(2026, 7, -5) == (2026, 2)


def test_parse_kpis_default_quando_invalido() -> None:
    assert g._parse_kpis("texto sem json") == ["faturamento"]
    assert g._parse_kpis('{"kpis": ["taxa_recompra", "xpto"]}') == ["taxa_recompra"]
