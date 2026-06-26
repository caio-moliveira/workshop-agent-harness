"""Carrega e tipa o golden dataset (`seed/evals/golden/narrativas.yaml`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN_PADRAO = RAIZ / "seed" / "evals" / "golden" / "narrativas.yaml"


@dataclass(frozen=True)
class ItemGolden:
    """Um caso do golden: a pergunta + as referências contra as quais o agente é medido."""

    id: str
    narrativa: str
    intencao: str  # central | secundario | controle
    dispara_enriquecimento: bool
    pergunta: str
    sql_esperado: str
    fontes_esperadas: list[str] = field(default_factory=list)
    distratores: list[str] = field(default_factory=list)
    recomendacao_esperada: str = ""

    @property
    def eh_controle(self) -> bool:
        """Item de controle (KPI saudável/sazonal) NÃO deve disparar enriquecimento."""
        return not self.dispara_enriquecimento


def _item(bruto: dict[str, Any]) -> ItemGolden:
    return ItemGolden(
        id=str(bruto["id"]),
        narrativa=str(bruto.get("narrativa", "")),
        intencao=str(bruto.get("intencao", "")),
        dispara_enriquecimento=bool(bruto.get("dispara_enriquecimento", False)),
        pergunta=str(bruto["pergunta"]),
        sql_esperado=str(bruto.get("sql_esperado", "")).strip(),
        fontes_esperadas=list(bruto.get("fontes_esperadas") or []),
        distratores=list(bruto.get("distratores") or []),
        recomendacao_esperada=str(bruto.get("recomendacao_esperada", "")).strip(),
    )


def carregar_golden(caminho: Path | None = None) -> list[ItemGolden]:
    """Lê o YAML do golden e devolve os itens tipados."""
    caminho = caminho or GOLDEN_PADRAO
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return [_item(b) for b in dados]
