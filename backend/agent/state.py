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
    periodo: str  # YYYY-MM alvo (mes atual + 1)
    mes_atual: str  # YYYY-MM do ultimo mes com dados
    kpis_foco: list[str]
    premissas: list[str]  # assuncoes declaradas no topo do relatorio (ambiguidade)
    precisa_clarificar: bool
    clarificacao: str  # pergunta de volta quando nem periodo nem KPI sao resolviveis
    achados: Annotated[list[dict[str, Any]], operator.add]
    fontes: Annotated[list[dict[str, Any]], operator.add]  # diagnostico/prescricao recuperados
    recomendacoes: Annotated[list[dict[str, Any]], operator.add]  # cada uma amarrada a uma fonte
    sql_log: Annotated[list[str], operator.add]
    relatorio: str
