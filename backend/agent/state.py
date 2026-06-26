"""Estado compartilhado do grafo. Topologia linear: cada campo é escrito por um nó só
(sem fan-out concorrente), então não precisa de reducer. O input é só `pergunta`."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class Recomendacao(TypedDict):
    """Uma recomendação amarrada à fonte que a sustenta (grounding)."""

    texto: str
    fonte: str
    resultado: str  # positivo | negativo | nulo (do doc de prescrição)


class HitEnriquecimento(TypedDict):
    """Trecho recuperado, em forma serializável (o checkpointer persiste o estado)."""

    fonte: str
    document: str
    resultado: str


class TurnoHistorico(TypedDict):
    """Um turno passado da conversa (persistido pelo checkpointer por thread)."""

    pergunta: str
    kpi_alvo: str
    dimensao: dict[str, str]
    fontes: list[str]  # fontes recomendadas naquele turno (para não repetir)


class EstadoAgente(TypedDict):
    """Memória do grafo `condensar → planejar → … → relatorio`. Persistida por thread."""

    pergunta: str
    # condensar (multi-turno)
    pergunta_resolvida: NotRequired[str]  # follow-up reescrito como pergunta autônoma
    historico: NotRequired[list[TurnoHistorico]]  # turnos anteriores (via checkpointer)
    fontes_ja_recomendadas: NotRequired[list[str]]  # do harness (durável) + histórico
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
    diagnostico_hits: NotRequired[list[HitEnriquecimento]]
    prescricao_hits: NotRequired[list[HitEnriquecimento]]
    fontes: NotRequired[list[str]]
    # relatorio
    diagnostico_texto: NotRequired[str]
    recomendacoes: NotRequired[list[Recomendacao]]
    relatorio: NotRequired[str]
