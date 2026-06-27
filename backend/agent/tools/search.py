"""Tool `search` — recuperação semântica no Qdrant, **sempre filtrada**.

Tool única parametrizada pela coleção (`camada_semantica` / `diagnostico` / `prescricao`):
o nó escolhe a coleção, não o LLM num laço. O enriquecimento (`diagnostico`/`prescricao`)
é **sempre** filtrado por `kpi_alvo` + dimensão e **nunca** por `data_ingestao`
(`periodo_referencia ≠ data_ingestao`). `periodo_referencia` é opcional (recorte sazonal).
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from qdrant_client import models as qmodels

from agent.tools.embeddings import Embedder

COLECOES = frozenset({"camada_semantica", "diagnostico", "prescricao"})
COLECOES_ENRIQUECIMENTO = frozenset({"diagnostico", "prescricao"})

# Filtrar pelo período do *negócio*, nunca pela data em que o doc foi indexado.
_CAMPO_PROIBIDO = "data_ingestao"


class FiltroInseguroError(ValueError):
    """Filtro recusado — viola o invariante de recuperação (ex.: `data_ingestao`)."""


class ColecaoInvalidaError(ValueError):
    """Coleção fora do conjunto conhecido, ou inadequada para a operação pedida."""


@dataclass(frozen=True)
class Trecho:
    """Um hit recuperado: a fonte rastreável + o texto + o score + o payload bruto."""

    fonte: str
    score: float
    document: str
    payload: dict[str, Any]


class ClienteQdrant(Protocol):
    """Contrato mínimo do cliente Qdrant (permite fake em teste).

    Tipos frouxos (`Any`) de propósito: o `QdrantClient` real tem assinatura bem mais ampla;
    o que importa é o nó chamar com `collection_name`/`query`/`query_filter`/`limit`.
    """

    def query_points(
        self,
        collection_name: str,
        query: Any,
        query_filter: Any,
        limit: int,
    ) -> Any: ...


def montar_filtro(filtros: Mapping[str, str | int]) -> qmodels.Filter:
    """Constrói o filtro MUST do Qdrant. Recusa `data_ingestao` e filtro vazio."""
    if _CAMPO_PROIBIDO in filtros:
        raise FiltroInseguroError(
            f"Filtrar por {_CAMPO_PROIBIDO!r} é proibido — use 'periodo_referencia'."
        )
    if not filtros:
        raise FiltroInseguroError(
            "A busca exige ao menos um filtro (periodo_referencia / kpi_alvo / dimensão)."
        )
    condicoes: list[qmodels.Condition] = [
        qmodels.FieldCondition(key=chave, match=qmodels.MatchValue(value=valor))
        for chave, valor in filtros.items()
    ]
    return qmodels.Filter(must=condicoes)


async def buscar(
    client: ClienteQdrant,
    embedder: Embedder,
    *,
    colecao: str,
    query: str,
    filtros: Mapping[str, str | int],
    limit: int = 5,
) -> list[Trecho]:
    """Embeda a query, aplica o filtro e devolve os trechos. Coleção escolhida pelo nó.

    Para coleções de enriquecimento exigimos `kpi_alvo` no filtro para que o invariante de
    escopo não dependa da disciplina do nó chamador.
    """
    if colecao not in COLECOES:
        raise ColecaoInvalidaError(f"Coleção desconhecida: {colecao!r}.")
    if colecao in COLECOES_ENRIQUECIMENTO and "kpi_alvo" not in filtros:
        raise FiltroInseguroError(
            f"Busca em {colecao!r} exige 'kpi_alvo' no filtro (use buscar_enriquecimento)."
        )
    filtro = montar_filtro(filtros)
    vetor = await embedder(query)
    resposta = await asyncio.to_thread(
        lambda: client.query_points(
            collection_name=colecao, query=vetor, query_filter=filtro, limit=limit
        )
    )
    trechos: list[Trecho] = []
    for ponto in resposta.points:
        payload: dict[str, Any] = ponto.payload or {}
        trechos.append(
            Trecho(
                fonte=str(payload.get("fonte", "?")),
                score=float(ponto.score),
                document=str(payload.get("document", "")),
                payload=payload,
            )
        )
    return trechos


async def buscar_enriquecimento(
    client: ClienteQdrant,
    embedder: Embedder,
    *,
    colecao: str,
    query: str,
    kpi_alvo: str,
    dimensao: Mapping[str, str | int],
    periodo_referencia: str | None = None,
    limit: int = 5,
) -> list[Trecho]:
    """Busca de enriquecimento: garante kpi_alvo + dimensão; periodo_referencia é opcional.

    O invariante é filtrar pela *família de período de negócio* (nunca `data_ingestao`); como
    as prescrições históricas vivem em vários `periodo_referencia`, ele não é exigido — só
    aplicado quando o nó quer recortar um período específico (sazonal).
    """
    if colecao not in COLECOES_ENRIQUECIMENTO:
        raise ColecaoInvalidaError(
            f"Enriquecimento só em {sorted(COLECOES_ENRIQUECIMENTO)}, não em {colecao!r}."
        )
    if not dimensao:
        raise FiltroInseguroError("O enriquecimento exige ao menos uma dimensão (ex.: regiao).")
    if _CAMPO_PROIBIDO in dimensao:
        raise FiltroInseguroError(f"Dimensão não pode ser {_CAMPO_PROIBIDO!r}.")
    filtros: dict[str, str | int] = {"kpi_alvo": kpi_alvo, **dimensao}
    if periodo_referencia is not None:
        filtros["periodo_referencia"] = periodo_referencia
    return await buscar(
        client, embedder, colecao=colecao, query=query, filtros=filtros, limit=limit
    )
