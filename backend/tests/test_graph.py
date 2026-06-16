"""Testes do grafo analitico (issues #19, #20) — sem DB nem LLM reais.

`run_sql` e `get_chat_model` sao substituidos por fakes deterministicos, provando a
topologia, a resolucao do periodo-alvo (mes atual + 1) e a leitura tendencia x sazonal.
"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import agent.graph as g
from agent.tools.run_sql import SqlResult


async def test_grafo_separa_tendencia_de_sazonalidade(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_sql(sql: str, **kw: object) -> SqlResult:
        if "MAX(data_pedido)" in sql:  # planejar resolve o mes atual
            return SqlResult(columns=["ano", "mes"], rows=[(2026, 6)], rowcount=1, sql=sql)
        if "EXTRACT(MONTH FROM p.data_pedido)" in sql:  # sazonal (mesmo mes, anos anteriores)
            return SqlResult(
                columns=["regiao", "real", "meta"],
                rows=[("Sul", 90.0, 100.0), ("Sudeste", 300.0, 300.0)],
                rowcount=2,
                sql=sql,
            )
        if "BETWEEN" in sql:  # tendencia (ultimos N meses)
            return SqlResult(
                columns=["regiao", "real", "meta"],
                rows=[("Sul", 100.0, 200.0), ("Sudeste", 500.0, 400.0)],
                rowcount=2,
                sql=sql,
            )
        return SqlResult(columns=[], rows=[], rowcount=0, sql=sql)

    fake_llm = FakeListChatModel(
        responses=['{"kpis": ["faturamento"]}', "No Sul ha queda real; sazonalidade tambem baixa."]
    )
    monkeypatch.setattr(g, "run_sql", fake_run_sql)
    monkeypatch.setattr(g, "get_chat_model", lambda tier="forte": fake_llm)

    state = await g.run_chat("como melhorar minhas vendas no proximo mes?")

    assert state["periodo"] == "2026-07"  # mes atual (2026-06) + 1
    assert state["mes_atual"] == "2026-06"
    achados = {a["dimensao"]: a for a in state["achados"]}
    # Sul: tendencia -50% e sazonal -10% -> abaixo em ambos.
    assert "regiao=Sul" in achados
    assert achados["regiao=Sul"]["abaixo_tendencia"] is True
    assert achados["regiao=Sul"]["abaixo_sazonal"] is True
    # Sudeste: tendencia +25% e sazonal 0% -> nao entra.
    assert "regiao=Sudeste" not in achados
    assert state["relatorio"]
    assert state["sql_log"]


def test_add_meses_trata_virada_de_ano() -> None:
    assert g._add_meses(2026, 6, 1) == (2026, 7)
    assert g._add_meses(2026, 12, 1) == (2027, 1)
    assert g._add_meses(2026, 7, -5) == (2026, 2)  # inicio da janela de tendencia


def test_parse_kpis_default_quando_invalido() -> None:
    assert g._parse_kpis("texto sem json") == ["faturamento"]
    assert g._parse_kpis('{"kpis": ["taxa_recompra", "xpto"]}') == ["taxa_recompra"]
