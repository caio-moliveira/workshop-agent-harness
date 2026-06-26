from __future__ import annotations

from decimal import Decimal

from evals.comparadores import (
    avaliar_grounding,
    resultset_nao_vazio,
    resultsets_iguais,
    routing_ok,
)


def test_grounding_recall_parcial_nao_passa() -> None:
    """Citar um subconjunto (sem extras/distratores) mas faltando uma esperada NÃO passa."""
    g = avaliar_grounding(
        citadas=["minio://a", "minio://b"],
        esperadas=["minio://a", "minio://b", "minio://c"],
        distratores=["minio://x"],
    )
    assert g.subconjunto_ok  # nada citado fora das esperadas
    assert g.sem_distratores
    assert g.faltantes == {"minio://c"}
    assert not g.recall_completo
    assert not g.ok  # recall incompleto reprova (fonte plantada must-find)
    assert 0.66 <= g.recall <= 0.67


def test_grounding_ok_quando_cita_exatamente_as_esperadas() -> None:
    """Cita todas as esperadas, sem extras nem distratores -> grounding aprovado."""
    g = avaliar_grounding(
        citadas=["minio://a", "minio://b"],
        esperadas=["minio://a", "minio://b"],
        distratores=["minio://x"],
    )
    assert g.ok
    assert g.recall_completo


def test_grounding_reprova_quando_cita_distrator() -> None:
    g = avaliar_grounding(
        citadas=["minio://a", "minio://x"],
        esperadas=["minio://a"],
        distratores=["minio://x"],
    )
    assert not g.sem_distratores
    assert not g.subconjunto_ok  # x não está entre as esperadas
    assert not g.ok


def test_grounding_controle_sem_esperadas_recall_1() -> None:
    g = avaliar_grounding(citadas=[], esperadas=[], distratores=[])
    assert g.recall == 1.0
    assert g.ok


def test_routing_ok() -> None:
    assert routing_ok(True, True)
    assert routing_ok(False, False)
    assert not routing_ok(True, False)  # controle que enriqueceu indevidamente


def test_resultset_nao_vazio() -> None:
    assert resultset_nao_vazio([{"n": 1}])
    assert not resultset_nao_vazio([])


def test_resultsets_iguais_ordem_e_decimal() -> None:
    a = [{"mes": "2026-01", "v": Decimal("0.477")}, {"mes": "2026-02", "v": Decimal("0.5")}]
    b = [{"mes": "2026-02", "v": 0.5}, {"mes": "2026-01", "v": 0.477}]
    assert resultsets_iguais(a, b)
    assert not resultsets_iguais(a, [{"mes": "2026-01", "v": 0.9}])
