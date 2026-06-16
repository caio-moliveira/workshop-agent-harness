"""Tool search: recuperacao semantica no Qdrant, sempre filtrada (issue #18).

Tool unica parametrizada pela colecao (escolhida pelo no do grafo, nunca por laco do
LLM). Coleções de enriquecimento (diagnostico, prescricao) exigem `periodo_referencia`;
`prescricao` exige tambem `kpi_alvo`. O filtro NUNCA usa `data_ingestao` — isso e
garantido estruturalmente: `data_ingestao` nao e um campo de SearchFilters.

A query e embeddada em runtime com o mesmo modelo da indexacao (text-embedding-3-large,
3072d). Clientes async sao criados por chamada (sem reuso entre event loops).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Condition, FieldCondition, Filter, MatchValue

from app.config import settings

COLLECTIONS = ("camada_semantica", "diagnostico", "prescricao")
_ENRIQUECIMENTO = ("diagnostico", "prescricao")
DEFAULT_LIMIT = 5

# Campos de filtro permitidos -> chave no payload. `data_ingestao` NAO entra aqui.
_FILTER_FIELDS = ("periodo_referencia", "regiao", "produto", "canal", "kpi_alvo", "resultado")


class SearchError(ValueError):
    """Busca rejeitada por um guardrail deterministico (colecao/filtro invalidos)."""


@dataclass
class SearchFilters:
    periodo_referencia: str | None = None
    regiao: str | None = None
    produto: str | None = None
    canal: str | None = None
    kpi_alvo: str | None = None
    resultado: str | None = None


@dataclass
class SearchHit:
    fonte: str | None
    score: float
    payload: dict[str, Any]


def _validate(collection: str, filters: SearchFilters) -> None:
    if collection not in COLLECTIONS:
        raise SearchError(f"colecao invalida: {collection!r} (use {COLLECTIONS})")
    if collection in _ENRIQUECIMENTO and not any(
        getattr(filters, campo) for campo in _FILTER_FIELDS
    ):
        # "Sempre filtrado": exige ao menos um filtro (dimensao, periodo ou kpi_alvo) —
        # buscas de enriquecimento (ex.: "o que funcionou em julhos anteriores") abrangem
        # varios periodos, entao periodo_referencia nao pode ser sempre obrigatorio.
        raise SearchError("coleção de enriquecimento exige ao menos um filtro")
    if collection == "prescricao" and not filters.kpi_alvo:
        raise SearchError("kpi_alvo e obrigatorio na colecao prescricao")


def _build_filter(filters: SearchFilters) -> Filter:
    must: list[Condition] = [
        FieldCondition(key=field, match=MatchValue(value=value))
        for field in _FILTER_FIELDS
        if (value := getattr(filters, field)) is not None
    ]
    return Filter(must=must)


async def embed_query(query: str) -> list[float]:
    """Embedda a query com o mesmo modelo da indexacao (provider-agnostic via config)."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        resp = await client.embeddings.create(model=settings.embed_model, input=query)
    finally:
        await client.close()
    return resp.data[0].embedding


async def search(
    collection: str,
    query: str,
    filters: SearchFilters,
    *,
    limit: int = DEFAULT_LIMIT,
) -> list[SearchHit]:
    """Busca semantica filtrada. A colecao e validada e escolhida pelo no, nao pelo LLM."""
    _validate(collection, filters)
    vector = await embed_query(query)
    client = AsyncQdrantClient(url=settings.qdrant_url)
    try:
        resp = await client.query_points(
            collection_name=collection,
            query=vector,
            query_filter=_build_filter(filters),
            limit=limit,
            with_payload=True,
        )
    finally:
        await client.close()
    return [
        SearchHit(
            fonte=(p.payload or {}).get("fonte"),
            score=p.score,
            payload=p.payload or {},
        )
        for p in resp.points
    ]
