"""Estado compartilhado do grafo. Topologia linear: cada campo é escrito por um nó só
(sem fan-out concorrente), então não precisa de reducer. O input é só `pergunta`."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from agent.tools.search import Trecho


class Recomendacao(TypedDict):
    """Uma recomendação amarrada à fonte que a sustenta (grounding)."""

    texto: str
    fonte: str
    resultado: str  # positivo | negativo | nulo (do doc de prescrição)


class EstadoAgente(TypedDict):
    """Memória do grafo `planejar → perna_quantitativa → enriquecer → relatorio`."""

    pergunta: str
    # planejar
    periodo_alvo: NotRequired[str]
    kpi_alvo: NotRequired[str]
    dimensao: NotRequired[dict[str, str]]
    premissas: NotRequired[dict[str, Any]]
    precisa_clarificar: NotRequired[bool]
    clarificacao: NotRequired[str]
    # perna_quantitativa
    sql_executado: NotRequired[list[str]]
    dados: NotRequired[dict[str, list[dict[str, Any]]]]
    dados_texto: NotRequired[str]
    saude: NotRequired[dict[str, Any]]  # veredito de saúde (fraco/motivo/parece_sazonal)
    # enriquecer
    diagnostico_hits: NotRequired[list[Trecho]]
    prescricao_hits: NotRequired[list[Trecho]]
    fontes: NotRequired[list[str]]
    # relatorio
    diagnostico_texto: NotRequired[str]
    recomendacoes: NotRequired[list[Recomendacao]]
    relatorio: NotRequired[str]
