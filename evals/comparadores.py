"""Comparadores puros do eval — sem I/O, totalmente testáveis offline.

Cobrem os sinais checáveis deterministicamente: grounding (fontes), routing (disparou
enriquecimento?) e validade de resultset (execution accuracy — ADR 0003).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ResultadoGrounding:
    """Conferência das fontes citadas contra esperadas + distratores."""

    citadas: set[str]
    esperadas: set[str]
    extras: set[str]  # citadas que não estão entre as esperadas
    faltantes: set[str]  # esperadas que não foram citadas
    distratores_citados: set[str]

    @property
    def subconjunto_ok(self) -> bool:
        """Toda fonte citada está entre as esperadas (sem citar nada de fora)."""
        return not self.extras

    @property
    def sem_distratores(self) -> bool:
        """Nenhum distrator (fonte plausível porém errada) foi citado."""
        return not self.distratores_citados

    @property
    def recall(self) -> float:
        """Fração das fontes esperadas que foram efetivamente citadas."""
        if not self.esperadas:
            return 1.0
        return len(self.esperadas & self.citadas) / len(self.esperadas)

    @property
    def recall_completo(self) -> bool:
        """Citou TODAS as fontes esperadas (cada uma é um doc plantado must-find)."""
        return not self.faltantes

    @property
    def ok(self) -> bool:
        """Grounding aprovado: cita exatamente as esperadas — subconjunto, sem distratores
        e sem faltar nenhuma (recall completo). Fontes plantadas são must-find."""
        return self.subconjunto_ok and self.sem_distratores and self.recall_completo


def avaliar_grounding(
    citadas: Sequence[str], esperadas: Sequence[str], distratores: Sequence[str]
) -> ResultadoGrounding:
    """Compara as fontes citadas pelo agente com o gabarito do golden."""
    c, e, d = set(citadas), set(esperadas), set(distratores)
    return ResultadoGrounding(
        citadas=c,
        esperadas=e,
        extras=c - e,
        faltantes=e - c,
        distratores_citados=c & d,
    )


def routing_ok(disparou_enriquecimento: bool, esperado: bool) -> bool:
    """O agente enriqueceu exatamente quando deveria (controles N4/N6 não enriquecem)."""
    return disparou_enriquecimento == esperado


def _normalizar_valor(v: Any) -> Any:
    """Decimal -> float p/ comparar resultsets vindos do banco sem ruído de tipo."""
    if isinstance(v, Decimal):
        return float(v)
    return v


def _normalizar_linhas(linhas: Sequence[dict[str, Any]]) -> list[tuple[tuple[str, Any], ...]]:
    return [tuple(sorted((k, _normalizar_valor(v)) for k, v in linha.items())) for linha in linhas]


def resultset_nao_vazio(linhas: Sequence[dict[str, Any]]) -> bool:
    """Execution accuracy (ADR 0003): a consulta executou e retornou linhas."""
    return len(linhas) > 0


def resultsets_iguais(
    a: Sequence[dict[str, Any]], b: Sequence[dict[str, Any]]
) -> bool:
    """Igualdade de resultset como conjunto de linhas (ordem-insensível, Decimal-tolerante)."""
    return sorted(_normalizar_linhas(a)) == sorted(_normalizar_linhas(b))
