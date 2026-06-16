"""Gera o spec do grafico do relatorio (issue #23).

Decisao (HANDOFF): matplotlib NAO e dependencia. Em vez de renderizar um PNG no
event loop, emitimos um spec Vega-Lite (JSON) deterministico a partir dos `achados`.
O cliente (frontend #25) renderiza; o backend persiste o spec no MinIO. Sem fonte de
imagem binaria, o artefato e inspecionavel e o app permanece runtime puro.
"""

from __future__ import annotations

from typing import Any

# (rotulo da serie, campo no achado)
_SERIES = (
    ("tendencia (6m)", "tendencia_gap_pct"),
    ("sazonal (2 anos)", "sazonal_gap_pct"),
)


def spec_gaps(achados: list[dict[str, Any]], periodo: str) -> dict[str, Any] | None:
    """Barras agrupadas: gap % vs meta por dimensao (tendencia x sazonal).

    Retorna `None` quando nao ha achado com gap numerico (ex.: pergunta clarificada
    ou KPI sem perna quantitativa) — nesse caso nao ha grafico a persistir.
    """
    valores: list[dict[str, Any]] = []
    for achado in achados:
        dimensao = achado.get("dimensao", "")
        for rotulo, campo in _SERIES:
            valor = achado.get(campo)
            if valor is not None:
                valores.append({"dimensao": dimensao, "serie": rotulo, "gap_pct": valor})
    if not valores:
        return None
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": f"Gap vs meta por dimensao — alvo {periodo}",
        "data": {"values": valores},
        "mark": "bar",
        "encoding": {
            "x": {"field": "dimensao", "type": "nominal", "title": "dimensao"},
            "xOffset": {"field": "serie", "type": "nominal"},
            "y": {"field": "gap_pct", "type": "quantitative", "title": "gap % vs meta"},
            "color": {"field": "serie", "type": "nominal", "title": "janela"},
        },
    }
