"""Catálogo do domínio: os KPIs e dimensões que o agente sabe medir.

Fonte única de verdade para o `planejar` (valida a escolha do LLM) e para os templates
de SQL (parametrizam a consulta). Mantém o vocabulário em português do negócio.
"""

from __future__ import annotations

# Os 4 KPIs de primeira classe (ver seed/schema.sql · metas.kpi).
KPIS: frozenset[str] = frozenset({"faturamento", "ticket_medio", "taxa_recompra", "taxa_conversao"})

# Dimensões de recorte -> coluna na tabela de dimensão correspondente.
DIMENSOES: frozenset[str] = frozenset({"regiao", "canal", "categoria"})

# Valores conhecidos por dimensão (para o LLM ancorar e para validar a escolha).
VALORES_DIMENSAO: dict[str, frozenset[str]] = {
    "regiao": frozenset({"Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"}),
    "canal": frozenset({"site_proprio", "marketplace", "loja_fisica"}),
    "categoria": frozenset(
        {"Eletrônicos", "Moda", "Beleza", "Casa", "Esporte", "Livros", "Brinquedos", "Mercado"}
    ),
}


def dimensao_valida(dimensao: dict[str, str]) -> bool:
    """True se a dimensão usa uma chave conhecida e (quando catalogado) um valor conhecido."""
    if not dimensao:
        return True  # agregado (sem recorte) é válido
    for chave, valor in dimensao.items():
        if chave not in DIMENSOES:
            return False
        validos = VALORES_DIMENSAO.get(chave)
        if validos is not None and valor not in validos:
            return False
    return True
