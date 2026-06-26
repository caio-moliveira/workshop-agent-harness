"""Decisão data-driven: o KPI está FRACO (merece diagnóstico) ou SAUDÁVEL/sazonal?

Determinística e testável (ADR 0004): roteia o grafo SEM o LLM. KPI abaixo da meta =
fraco (enriquece, mesmo que a queda seja sazonal — estar abaixo do alvo é o problema).
No/acima da meta = saudável (a variação, inclusive a alta sazonal de fim de ano, não é
deficit). Sem meta cadastrada, cai no comparativo sazonal (queda vs anos anteriores).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Saude:
    """Veredito de saúde do KPI no período-alvo."""

    fraco: bool  # True = abaixo do alvo / em queda real -> enriquecer
    motivo: str
    parece_sazonal: bool = False  # a variação é consistente com o padrão de anos anteriores


def _valor(linhas: Sequence[dict[str, Any]], chave: str) -> float | None:
    """Valor da única/primeira linha relevante — usado para a meta (consulta com LIMIT 1)."""
    if not linhas:
        return None
    bruto = linhas[-1].get(chave)
    return float(bruto) if bruto is not None else None


def _ultimo_da_tendencia(linhas: Sequence[dict[str, Any]]) -> float | None:
    """Valor do mês mais recente — ordena por `mes` (YYYY-MM) em vez de confiar na posição."""
    candidatas = [r for r in linhas if r.get("valor") is not None]
    if not candidatas:
        return None
    recente = max(candidatas, key=lambda r: str(r.get("mes", "")))
    return float(recente["valor"])


def avaliar_saude(dados: dict[str, list[dict[str, Any]]]) -> Saude:
    """Classifica o KPI a partir dos resultsets (tendência/sazonal/meta)."""
    tendencia = dados.get("tendencia", [])
    ultimo = _ultimo_da_tendencia(tendencia)
    meta = _valor(dados.get("meta", []), "valor_meta")
    sazonais = [float(r["valor"]) for r in dados.get("sazonal", []) if r.get("valor") is not None]

    if ultimo is None:
        return Saude(fraco=False, motivo="sem dados de tendência — nada a diagnosticar")

    # A variação parece sazonal se o valor recente está dentro da faixa dos anos anteriores.
    parece_sazonal = bool(sazonais) and min(sazonais) * 0.9 <= ultimo <= max(sazonais) * 1.1

    if meta is not None:
        if ultimo < meta:
            return Saude(fraco=True, motivo="abaixo da meta", parece_sazonal=parece_sazonal)
        return Saude(fraco=False, motivo="no/acima da meta", parece_sazonal=parece_sazonal)

    # Sem meta: fraco só se houver queda real (pior que todos os anos anteriores).
    if sazonais and ultimo < min(sazonais):
        return Saude(fraco=True, motivo="queda vs anos anteriores", parece_sazonal=False)
    return Saude(fraco=False, motivo="estável vs anos anteriores", parece_sazonal=parece_sazonal)
