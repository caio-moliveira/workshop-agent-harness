from __future__ import annotations

from datetime import date

import pytest

from agent.periodo import proximo_mes, resolver_janelas


def test_proximo_mes_dentro_do_ano() -> None:
    assert proximo_mes(2026, 6) == (2026, 7)


def test_proximo_mes_vira_o_ano() -> None:
    """Dezembro -> janeiro do ano seguinte (virada de ano)."""
    assert proximo_mes(2026, 12) == (2027, 1)


def test_periodo_alvo_da_ancora_padrao() -> None:
    j = resolver_janelas(date(2026, 6, 16))
    assert j.periodo_alvo == "2026-07"
    assert (j.ano_alvo, j.mes_alvo) == (2026, 7)


def test_periodo_alvo_na_virada_de_ano() -> None:
    j = resolver_janelas(date(2026, 12, 10))
    assert j.periodo_alvo == "2027-01"
    assert (j.ano_alvo, j.mes_alvo) == (2027, 1)
    assert j.anos_sazonais == (2026, 2025)


def test_janela_tendencia_6_meses() -> None:
    j = resolver_janelas(date(2026, 6, 16))
    assert j.inicio_tendencia == date(2026, 1, 1)


def test_janela_tendencia_cruza_o_ano() -> None:
    j = resolver_janelas(date(2026, 2, 16))
    assert j.inicio_tendencia == date(2025, 9, 1)


@pytest.mark.parametrize(
    ("hoje", "esperado"),
    [
        (date(2025, 1, 31), "2025-02"),
        (date(2025, 11, 1), "2025-12"),
        (date(2025, 12, 31), "2026-01"),
    ],
)
def test_periodo_alvo_varios(hoje: date, esperado: str) -> None:
    assert resolver_janelas(hoje).periodo_alvo == esperado
