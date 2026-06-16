"""Testes da tool search (issue #18).

Validacoes deterministicas (enum, filtro obrigatorio, nunca data_ingestao) sao
testadas sem rede. O teste de filtro usa um vetor real da colecao como query
(monkeypatch em embed_query) — prova o filtro contra dados reais sem chamar a OpenAI.
Pula se o Qdrant estiver indisponivel.
"""

from typing import cast

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition

from agent.tools.search import (
    SearchError,
    SearchFilters,
    _build_filter,
    _validate,
    search,
)
from app.config import settings

# ---- Validacoes deterministicas (sem rede) ----


def test_rejeita_colecao_invalida() -> None:
    with pytest.raises(SearchError):
        _validate("inexistente", SearchFilters(periodo_referencia="2024-06"))


def test_exige_algum_filtro_em_enriquecimento() -> None:
    with pytest.raises(SearchError):
        _validate("diagnostico", SearchFilters())  # nenhum filtro -> recusa


def test_enriquecimento_aceita_so_dimensao() -> None:
    _validate("diagnostico", SearchFilters(regiao="Sul"))  # dimensao basta (sem periodo)


def test_exige_kpi_alvo_em_prescricao() -> None:
    with pytest.raises(SearchError):
        _validate("prescricao", SearchFilters(periodo_referencia="2025-11"))


def test_camada_semantica_nao_exige_periodo() -> None:
    _validate("camada_semantica", SearchFilters())  # nao deve levantar


def test_build_filter_nunca_usa_data_ingestao() -> None:
    flt = _build_filter(SearchFilters(periodo_referencia="2024-06", produto="Livros & Papelaria"))
    keys = {c.key for c in (flt.must or []) if isinstance(c, FieldCondition)}
    assert "data_ingestao" not in keys
    assert keys == {"periodo_referencia", "produto"}


# ---- Integracao (skip se Qdrant indisponivel) ----


async def _qdrant_indisponivel() -> bool:
    client = AsyncQdrantClient(url=settings.qdrant_url)
    try:
        await client.get_collections()
        return False
    except Exception:
        return True
    finally:
        await client.close()


async def test_search_filtra_e_exclui_ruido(monkeypatch: pytest.MonkeyPatch) -> None:
    if await _qdrant_indisponivel():
        pytest.skip("Qdrant indisponivel")

    # Usa um vetor real da colecao como query (sem chamar OpenAI).
    client = AsyncQdrantClient(url=settings.qdrant_url)
    try:
        records, _ = await client.scroll(
            collection_name="diagnostico", limit=1, with_vectors=True, with_payload=True
        )
    finally:
        await client.close()
    if not records:
        pytest.skip("colecao diagnostico vazia")
    raw = records[0].vector
    assert isinstance(raw, list)
    vetor = cast(list[float], raw)

    async def fake_embed(_q: str) -> list[float]:
        return vetor

    monkeypatch.setattr("agent.tools.search.embed_query", fake_embed)

    # Filtro casa com o doc de 2024-06 (Livros & Papelaria): retorna so o que bate.
    hits = await search(
        "diagnostico",
        "qualquer",
        SearchFilters(periodo_referencia="2024-06", produto="Livros & Papelaria"),
    )
    assert hits, "esperava ao menos uma fonte para 2024-06"
    assert all(h.payload.get("periodo_referencia") == "2024-06" for h in hits)

    # Filtro impossivel -> nada: prova que o filtro exclui o ruido de fundo.
    vazio = await search(
        "diagnostico", "qualquer", SearchFilters(periodo_referencia="1999-01")
    )
    assert vazio == []
