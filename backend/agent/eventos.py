"""Eventos incrementais emitidos pelos nós (stream_mode='custom').

O service traduz cada evento numa linha SSE. Manter o vocabulário aqui evita que os tipos
de evento se espalhem entre nó e router.
"""

from __future__ import annotations

from typing import Any, Literal

TipoEvento = Literal["premissas", "sql", "dados", "fontes", "diagnostico", "recomendacao", "fim"]


def evento(tipo: TipoEvento, **dados: Any) -> dict[str, Any]:
    """Monta o dicionário de um evento de stream (tipo + carga)."""
    return {"tipo": tipo, **dados}
