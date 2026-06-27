"""Carrega o golden dataset (narrativas.yaml) em casos tipados.

O dataset é a fonte da verdade da avaliação e vive em `seed/evals/golden/` (fora do
backend, versionado). Aqui só lemos e tipamos — não geramos nem alteramos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Raiz do repo: backend/evals/golden.py -> sobe 3 níveis.
_RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_GOLDEN = _RAIZ / "seed" / "evals" / "golden" / "narrativas.yaml"


@dataclass(frozen=True)
class CasoGolden:
    """Um caso do golden: pergunta + referências de roteamento/grounding/desfecho."""

    id: str
    narrativa: str
    intencao: str  # central | secundario | controle
    dispara_enriquecimento: bool
    pergunta: str
    sql_esperado: str
    fontes_esperadas: list[str]
    distratores: list[str]
    recomendacao_esperada: str

    @property
    def eh_controle(self) -> bool:
        """Controle = KPI saudável; o agente NÃO deve enriquecer (n4/n6)."""
        return not self.dispara_enriquecimento


def _para_caso(bruto: dict[str, Any]) -> CasoGolden:
    return CasoGolden(
        id=str(bruto["id"]),
        narrativa=str(bruto.get("narrativa", "")),
        intencao=str(bruto.get("intencao", "")),
        dispara_enriquecimento=bool(bruto.get("dispara_enriquecimento", False)),
        pergunta=str(bruto["pergunta"]),
        sql_esperado=str(bruto.get("sql_esperado", "")),
        fontes_esperadas=list(bruto.get("fontes_esperadas") or []),
        distratores=list(bruto.get("distratores") or []),
        recomendacao_esperada=str(bruto.get("recomendacao_esperada", "")).strip(),
    )


def carregar_golden(caminho: Path = CAMINHO_GOLDEN) -> list[CasoGolden]:
    """Lê o YAML e devolve os casos na ordem do arquivo."""
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, list):
        raise ValueError(f"Golden inválido em {caminho}: esperava uma lista de casos.")
    return [_para_caso(item) for item in dados]
