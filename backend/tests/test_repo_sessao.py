"""Integracao do repo de sessao/turnos no schema `harness` (issue #24).

Exercita o SQL real (criar_sessao, criar_run com pergunta_reescrita, historico_sessao,
fontes_prescricao_da_sessao). Pula se o Postgres estiver indisponivel. Limpa ao final
via CASCADE da sessao (apaga runs + fontes do teste).
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from harness import repo


async def _db_indisponivel() -> bool:
    try:
        async with repo._admin_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return False
    except Exception:
        return True


async def test_sessao_historico_e_fontes_prescricao() -> None:
    if await _db_indisponivel():
        pytest.skip("Postgres indisponivel")

    sessao_id = await repo.criar_sessao("teste-24")
    try:
        # Turno 1: pergunta central, recomenda uma prescricao.
        r1 = await repo.criar_run("como vao as vendas no Sul?", sessao_id, "vendas no Sul (2026-07)")
        await repo.registrar_fonte(r1, "prescricao", fonte="presc/sul-frete.md", payload={"x": 1})
        await repo.registrar_fonte(r1, "diagnostico", fonte="diag/sul.md", payload={"y": 2})
        await repo.finalizar_run(r1, "Relatorio do turno 1.")

        # Turno 2 ainda em andamento (nao deve entrar no historico de concluidos).
        await repo.criar_run("e no Sudeste?", sessao_id, "vendas no Sudeste (2026-07)")

        hist = await repo.historico_sessao(sessao_id)
        assert len(hist) == 1  # so o turno concluido
        assert hist[0]["pergunta_reescrita"] == "vendas no Sul (2026-07)"
        assert hist[0]["relatorio"] == "Relatorio do turno 1."

        # So a fonte de prescricao volta (diagnostico nao se suprime).
        fontes = await repo.fontes_prescricao_da_sessao(sessao_id)
        assert fontes == ["presc/sul-frete.md"]
    finally:
        async with repo._admin_engine().begin() as conn:
            await conn.execute(
                text("DELETE FROM harness.sessoes WHERE id = :s"), {"s": sessao_id}
            )
