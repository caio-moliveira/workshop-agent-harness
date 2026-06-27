from __future__ import annotations

from evals.golden import carregar_golden


def test_golden_carrega_os_seis_casos() -> None:
    casos = carregar_golden()
    ids = [c.id for c in casos]
    assert len(casos) == 6
    assert ids == [
        "n1-recompra-sul",
        "n2-eletronicos-marketplace",
        "n3-conversao-site",
        "n4-beleza-nordeste",
        "n5-loja-fisica",
        "n6-ticket-sazonal",
    ]


def test_controles_nao_disparam_enriquecimento() -> None:
    """n4/n6 são controles: sem fontes esperadas e não enriquecem."""
    casos = {c.id: c for c in carregar_golden()}
    for cid in ("n4-beleza-nordeste", "n6-ticket-sazonal"):
        c = casos[cid]
        assert c.eh_controle
        assert c.fontes_esperadas == []


def test_casos_centrais_tem_fontes_e_sql() -> None:
    """Casos que enriquecem trazem fontes esperadas e SQL de referência."""
    for c in carregar_golden():
        if c.dispara_enriquecimento:
            assert c.fontes_esperadas, f"{c.id} deveria ter fontes esperadas"
        assert c.sql_esperado.strip().lower().startswith(("select", "with"))
