"""Tool `search` — recuperação semântica no Qdrant, **sempre filtrada**.

Tool única parametrizada pela coleção (`camada_semantica` / `diagnostico` / `prescricao`):
o nó escolhe a coleção, não o LLM num laço. O enriquecimento (`diagnostico`/`prescricao`)
é **sempre** filtrado por `periodo_referencia` + dimensão + `kpi_alvo` e **nunca** por
`data_ingestao` (`periodo_referencia ≠ data_ingestao` — confundir os dois é o erro clássico).
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
    """Contrato mínimo do cliente Qdrant (permite fake em teste)."""

    def query_points(
        self,
        collection_name: str,
        query: list[float],
        query_filter: qmodels.Filter | None,
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

    Para coleções de enriquecimento (`diagnostico`/`prescricao`) o caminho correto é
    `buscar_enriquecimento` — aqui exigimos `periodo_referencia` + `kpi_alvo` no filtro
    para que o invariante não dependa da disciplina do nó chamador.
    """
    if colecao not in COLECOES:
        raise ColecaoInvalidaError(f"Coleção desconhecida: {colecao!r}.")
    if colecao in COLECOES_ENRIQUECIMENTO:
        faltando = {"periodo_referencia", "kpi_alvo"} - set(filtros)
        if faltando:
            raise FiltroInseguroError(
                f"Busca em {colecao!r} exige {sorted(faltando)} no filtro "
                "(use buscar_enriquecimento)."
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
    periodo_referencia: str,
    kpi_alvo: str,
    dimensao: Mapping[str, str | int],
    limit: int = 5,
) -> list[Trecho]:
    """Busca de enriquecimento: garante periodo_referencia + kpi_alvo + dimensão no filtro."""
    if colecao not in COLECOES_ENRIQUECIMENTO:
        raise ColecaoInvalidaError(
            f"Enriquecimento só em {sorted(COLECOES_ENRIQUECIMENTO)}, não em {colecao!r}."
        )
    if not dimensao:
        raise FiltroInseguroError("O enriquecimento exige ao menos uma dimensão (ex.: regiao).")
    if _CAMPO_PROIBIDO in dimensao:
        raise FiltroInseguroError(f"Dimensão não pode ser {_CAMPO_PROIBIDO!r}.")
    filtros: dict[str, str | int] = {
        "periodo_referencia": periodo_referencia,
        "kpi_alvo": kpi_alvo,
        **dimensao,
    }
    return await buscar(
        client, embedder, colecao=colecao, query=query, filtros=filtros, limit=limit
    )
