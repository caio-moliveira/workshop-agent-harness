from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from qdrant_client import models as qmodels

from agent.tools.search import (
    ColecaoInvalidaError,
    FiltroInseguroError,
    buscar,
    buscar_enriquecimento,
    montar_filtro,
)


class FakeClient:
    """Captura a chamada ao Qdrant (sobretudo o query_filter) e devolve pontos canned."""

    def __init__(self, points: list[Any] | None = None) -> None:
        self.points = points or []
        self.ultima_chamada: dict[str, Any] | None = None

    def query_points(
        self,
        collection_name: str,
        query: list[float],
        query_filter: qmodels.Filter | None,
        limit: int,
    ) -> Any:
        self.ultima_chamada = {
            "collection_name": collection_name,
            "query": query,
            "query_filter": query_filter,
            "limit": limit,
        }
        return SimpleNamespace(points=self.points)


async def _embedder_fake(_texto: str) -> list[float]:
    return [0.1, 0.2, 0.3]


def _chaves_do_filtro(flt: qmodels.Filter | None) -> set[str]:
    assert flt is not None
    return {c.key for c in (flt.must or [])}  # type: ignore[union-attr]


def test_montar_filtro_rejeita_data_ingestao() -> None:
    """O invariante de ouro: nunca filtrar por data_ingestao."""
    with pytest.raises(FiltroInseguroError):
        montar_filtro({"periodo_referencia": "2026-07", "data_ingestao": "2026-06-16"})


def test_montar_filtro_rejeita_vazio() -> None:
    with pytest.raises(FiltroInseguroError):
        montar_filtro({})


def test_montar_filtro_inclui_todas_as_chaves() -> None:
    flt = montar_filtro({"kpi_alvo": "taxa_recompra", "regiao": "Sul"})
    assert _chaves_do_filtro(flt) == {"kpi_alvo", "regiao"}


async def test_enriquecimento_filtra_kpi_e_dimensao_sem_periodo() -> None:
    """Por padrão o filtro carrega kpi_alvo + dimensão e NÃO força periodo_referencia."""
    client = FakeClient(
        points=[SimpleNamespace(score=0.8, payload={"fonte": "minio://x", "document": "d"})]
    )
    trechos = await buscar_enriquecimento(
        client,
        _embedder_fake,
        colecao="prescricao",
        query="q",
        kpi_alvo="taxa_recompra",
        dimensao={"regiao": "Sul"},
    )
    chaves = _chaves_do_filtro(client.ultima_chamada["query_filter"])  # type: ignore[index]
    assert {"kpi_alvo", "regiao"} <= chaves
    assert "periodo_referencia" not in chaves
    assert "data_ingestao" not in chaves
    assert trechos[0].fonte == "minio://x"


async def test_enriquecimento_aplica_periodo_quando_pedido() -> None:
    client = FakeClient(points=[])
    await buscar_enriquecimento(
        client,
        _embedder_fake,
        colecao="prescricao",
        query="q",
        kpi_alvo="faturamento",
        dimensao={"canal": "marketplace"},
        periodo_referencia="2025-11",
    )
    chaves = _chaves_do_filtro(client.ultima_chamada["query_filter"])  # type: ignore[index]
    assert {"kpi_alvo", "canal", "periodo_referencia"} <= chaves


async def test_enriquecimento_recusa_camada_semantica() -> None:
    with pytest.raises(ColecaoInvalidaError):
        await buscar_enriquecimento(
            FakeClient(),
            _embedder_fake,
            colecao="camada_semantica",
            query="x",
            kpi_alvo="faturamento",
            dimensao={"regiao": "Sul"},
        )


async def test_enriquecimento_exige_dimensao() -> None:
    with pytest.raises(FiltroInseguroError):
        await buscar_enriquecimento(
            FakeClient(),
            _embedder_fake,
            colecao="diagnostico",
            query="x",
            kpi_alvo="faturamento",
            dimensao={},
        )


async def test_enriquecimento_recusa_data_ingestao_na_dimensao() -> None:
    with pytest.raises(FiltroInseguroError):
        await buscar_enriquecimento(
            FakeClient(),
            _embedder_fake,
            colecao="diagnostico",
            query="x",
            kpi_alvo="faturamento",
            dimensao={"data_ingestao": "2026-06-16"},
        )


async def test_buscar_recusa_colecao_desconhecida() -> None:
    with pytest.raises(ColecaoInvalidaError):
        await buscar(
            FakeClient(),
            _embedder_fake,
            colecao="inexistente",
            query="x",
            filtros={"kpi_alvo": "faturamento"},
        )


async def test_buscar_enriquecimento_exige_kpi_alvo() -> None:
    """Coleção de enriquecimento sem kpi_alvo no filtro é barrada (não depende do nó)."""
    with pytest.raises(FiltroInseguroError):
        await buscar(
            FakeClient(),
            _embedder_fake,
            colecao="prescricao",
            query="x",
            filtros={"regiao": "Sul"},
        )


async def test_buscar_usa_vetor_do_embedder() -> None:
    client = FakeClient(points=[])
    await buscar(
        client,
        _embedder_fake,
        colecao="diagnostico",
        query="x",
        filtros={"kpi_alvo": "taxa_recompra", "regiao": "Sul"},
    )
    assert client.ultima_chamada["query"] == [0.1, 0.2, 0.3]  # type: ignore[index]
