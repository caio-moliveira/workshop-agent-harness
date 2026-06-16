"""Testes do grafo analitico (issue #19) — sem DB nem LLM reais.

`run_sql` e `get_chat_model` sao substituidos por fakes deterministicos, provando a
topologia planejar -> perna_quantitativa -> relatorio e a logica de "abaixo da meta".
"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import agent.graph as g
from agent.tools.run_sql import SqlResult


async def test_grafo_identifica_kpi_abaixo_da_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_sql(sql: str, **kw: object) -> SqlResult:
        if "FROM negocio.metas ORDER BY" in sql:
            return SqlResult(columns=["ano", "mes"], rows=[(2026, 5)], rowcount=1, sql=sql)
        if "COALESCE(SUM(p.valor_total)" in sql:
            return SqlResult(
                columns=["regiao", "realizado"],
                rows=[("Sul", 100.0), ("Sudeste", 500.0)],
                rowcount=2,
                sql=sql,
            )
        if "valor_meta" in sql:
            return SqlResult(
                columns=["regiao", "valor_meta"],
                rows=[("Sul", 200.0), ("Sudeste", 400.0)],
                rowcount=2,
                sql=sql,
            )
        return SqlResult(columns=[], rows=[], rowcount=0, sql=sql)

    fake_llm = FakeListChatModel(
        responses=['{"kpis": ["faturamento"]}', "Sul ficou abaixo da meta de faturamento."]
    )
    monkeypatch.setattr(g, "run_sql", fake_run_sql)
    monkeypatch.setattr(g, "get_chat_model", lambda tier="forte": fake_llm)

    state = await g.run_chat("como melhorar o faturamento no proximo mes?")

    assert state["periodo"] == "2026-05"
    achados = state["achados"]
    # Sul (100 < 200) entra; Sudeste (500 >= 400) nao.
    assert any(a["dimensao"] == "regiao=Sul" for a in achados)
    assert all(a["dimensao"] != "regiao=Sudeste" for a in achados)
    assert state["achados"][0]["gap_pct"] < 0
    assert "abaixo da meta" in state["relatorio"]
    assert state["sql_log"]  # SQL executado registrado para auditoria


def test_proximo_mes_trata_virada_de_ano() -> None:
    assert g._proximo_mes(2026, 5) == "2026-06-01"
    assert g._proximo_mes(2026, 12) == "2027-01-01"


def test_parse_kpis_default_quando_invalido() -> None:
    assert g._parse_kpis("texto sem json") == ["faturamento"]
    assert g._parse_kpis('{"kpis": ["taxa_recompra", "xpto"]}') == ["taxa_recompra"]
