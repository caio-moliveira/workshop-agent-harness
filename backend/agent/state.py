"""Estado do sub-grafo analitico (issue #19).

Stateless por design: o estado de sessao vive no schema `harness`. Reducers em
`achados`/`sql_log` permitem que nos acumulem (preparado para o fan-out da #21).
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


class ChatState(TypedDict, total=False):
    pergunta: str
    periodo: str  # YYYY-MM resolvido
    kpis_foco: list[str]
    achados: Annotated[list[dict[str, Any]], operator.add]
    sql_log: Annotated[list[str], operator.add]
    relatorio: str
