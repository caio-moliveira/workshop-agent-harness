"""Resolução de janelas temporais a partir de uma âncora "hoje" fixa e injetável.

Determinístico de propósito: o período-alvo e as janelas de tendência/sazonal saem da
âncora (`settings.hoje_ancora`), não do relógio — é o que torna os evals reproduzíveis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class JanelasTemporais:
    """As janelas que o agente compara: alvo (mês+1), tendência (6m) e sazonal (anos -1/-2)."""

    periodo_alvo: str  # "YYYY-MM" — mês de referência + 1
    ano_alvo: int
    mes_alvo: int
    inicio_tendencia: date  # 1º dia, 6 meses antes do mês-âncora (inclusive)
    anos_sazonais: tuple[int, ...]  # mesmo mês-alvo nos 2 anos anteriores


def proximo_mes(ano: int, mes: int) -> tuple[int, int]:
    """(ano, mes) do mês seguinte, tratando a virada de ano (dez -> jan do ano+1)."""
    if mes == 12:
        return ano + 1, 1
    return ano, mes + 1


def _subtrai_meses(ano: int, mes: int, n: int) -> tuple[int, int]:
    """(ano, mes) de `n` meses atrás — aritmética modular em base 12."""
    indice = (ano * 12 + (mes - 1)) - n
    return indice // 12, (indice % 12) + 1


def resolver_janelas(hoje: date, *, meses_tendencia: int = 6) -> JanelasTemporais:
    """Deriva as janelas a partir da âncora. Período-alvo = mês de `hoje` + 1."""
    ano_alvo, mes_alvo = proximo_mes(hoje.year, hoje.month)
    ano_ini, mes_ini = _subtrai_meses(hoje.year, hoje.month, meses_tendencia - 1)
    return JanelasTemporais(
        periodo_alvo=f"{ano_alvo:04d}-{mes_alvo:02d}",
        ano_alvo=ano_alvo,
        mes_alvo=mes_alvo,
        inicio_tendencia=date(ano_ini, mes_ini, 1),
        anos_sazonais=(ano_alvo - 1, ano_alvo - 2),
    )
