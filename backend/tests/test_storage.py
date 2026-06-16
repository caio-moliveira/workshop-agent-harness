"""Testes de charts + persistencia no MinIO (issue #23).

`charts.spec_gaps` e deterministico e roda sem rede. A persistencia tem um teste de
integracao que grava e le de volta do MinIO real, pulado se o MinIO estiver fora (mesma
convencao dos testes de Postgres/Qdrant). Usa um bucket de teste para nao sujar dados.
"""

from __future__ import annotations

import json

import pytest

from app.config import settings
from app.services import charts, storage

# ---- charts.spec_gaps (deterministico, sem rede) ----


def test_spec_gaps_monta_barras_por_dimensao() -> None:
    achados = [
        {"dimensao": "regiao=Sul", "tendencia_gap_pct": -5.0, "sazonal_gap_pct": -3.0},
        {"dimensao": "regiao=Sudeste", "tendencia_gap_pct": -2.0, "sazonal_gap_pct": None},
    ]
    spec = charts.spec_gaps(achados, "2026-07")
    assert spec is not None
    assert spec["mark"] == "bar"
    valores = spec["data"]["values"]
    # Sul tem 2 series; Sudeste so tendencia (sazonal None e omitido).
    assert len(valores) == 3
    assert {"dimensao": "regiao=Sul", "serie": "tendencia (6m)", "gap_pct": -5.0} in valores


def test_spec_gaps_retorna_none_sem_achados() -> None:
    assert charts.spec_gaps([], "2026-07") is None
    # achado sem gap numerico tambem nao gera grafico.
    assert charts.spec_gaps([{"dimensao": "regiao=Sul"}], "2026-07") is None


# ---- Persistencia no MinIO (skip se indisponivel) ----


def _minio_indisponivel() -> bool:
    try:
        storage._minio().list_buckets()
        return False
    except Exception:
        return True


async def test_persistir_artefatos_grava_no_minio(monkeypatch: pytest.MonkeyPatch) -> None:
    if _minio_indisponivel():
        pytest.skip("MinIO indisponivel")

    # Bucket de teste para nao tocar o bucket de producao.
    monkeypatch.setattr(settings, "minio_bucket_relatorios", "relatorios-teste")
    storage._client = None  # forca recriacao do cliente com a config corrente

    run_id = "run-teste-23"
    spec = charts.spec_gaps(
        [{"dimensao": "regiao=Sul", "tendencia_gap_pct": -5.0, "sazonal_gap_pct": -3.0}],
        "2026-07",
    )
    artefatos = await storage.persistir_artefatos(run_id, "# Relatorio\nconteudo.", spec)

    assert artefatos["relatorio"] == f"relatorios-teste/{run_id}/relatorio.md"
    assert artefatos["grafico"] == f"relatorios-teste/{run_id}/grafico.json"

    # Le de volta: o objeto existe e o conteudo bate.
    client = storage._minio()
    rel = client.get_object("relatorios-teste", f"{run_id}/relatorio.md")
    try:
        assert rel.read().decode("utf-8") == "# Relatorio\nconteudo."
    finally:
        rel.close()
        rel.release_conn()
    graf = client.get_object("relatorios-teste", f"{run_id}/grafico.json")
    try:
        assert json.loads(graf.read())["mark"] == "bar"
    finally:
        graf.close()
        graf.release_conn()

    storage._client = None  # nao vaza o cliente para outros testes
