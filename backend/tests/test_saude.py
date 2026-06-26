from __future__ import annotations

from typing import Any

from agent.saude import avaliar_saude

Dados = dict[str, list[dict[str, Any]]]


def test_abaixo_da_meta_eh_fraco() -> None:
    """Valor recente < meta -> fraco (enriquece), mesmo se a queda for sazonal."""
    dados: Dados = {
        "tendencia": [{"mes": "2026-01", "valor": 0.477}],
        "sazonal": [{"ano": 2025, "valor": 0.61}],
        "meta": [{"valor_meta": 0.65}],
    }
    s = avaliar_saude(dados)
    assert s.fraco
    assert "meta" in s.motivo


def test_acima_da_meta_eh_saudavel() -> None:
    """N4-like: acima da meta -> saudável (não enriquece)."""
    dados: Dados = {
        "tendencia": [{"mes": "2026-01", "valor": 1200.0}],
        "sazonal": [{"ano": 2025, "valor": 1000.0}],
        "meta": [{"valor_meta": 1100.0}],
    }
    assert not avaliar_saude(dados).fraco


def test_alta_sazonal_acima_da_meta_nao_eh_fraco() -> None:
    """N6-like: alta sazonal acima do alvo não é deficit."""
    dados: Dados = {
        "tendencia": [{"mes": "2026-01", "valor": 260.0}],
        "sazonal": [{"ano": 2025, "valor": 240.0}, {"ano": 2024, "valor": 230.0}],
        "meta": [{"valor_meta": 250.0}],
    }
    assert not avaliar_saude(dados).fraco


def test_sem_meta_usa_comparativo_sazonal() -> None:
    """Sem meta: fraco só se houver queda real (pior que todos os anos anteriores)."""
    queda: Dados = {
        "tendencia": [{"mes": "2026-01", "valor": 100.0}],
        "sazonal": [{"ano": 2025, "valor": 150.0}, {"ano": 2024, "valor": 140.0}],
        "meta": [],
    }
    assert avaliar_saude(queda).fraco

    estavel: Dados = {
        "tendencia": [{"mes": "2026-01", "valor": 145.0}],
        "sazonal": [{"ano": 2025, "valor": 150.0}, {"ano": 2024, "valor": 140.0}],
        "meta": [],
    }
    assert not avaliar_saude(estavel).fraco


def test_sem_tendencia_nao_eh_fraco() -> None:
    """Sem dados de tendência não há o que diagnosticar -> não enriquece."""
    vazio: Dados = {"tendencia": [], "sazonal": [], "meta": []}
    assert not avaliar_saude(vazio).fraco
