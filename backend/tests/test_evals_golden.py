from __future__ import annotations

from evals.golden import carregar_golden


def test_golden_carrega_os_seis_itens() -> None:
    """O golden plantado tem as 6 narrativas (N1..N6) com campos do contrato."""
    itens = carregar_golden()
    assert len(itens) == 6
    ids = {i.id for i in itens}
    assert "n1-recompra-sul" in ids


def test_golden_controles_nao_disparam_enriquecimento() -> None:
    """N4 e N6 são controles: dispara_enriquecimento=false e fontes_esperadas vazias."""
    itens = {i.narrativa: i for i in carregar_golden()}
    for nar in ("N4", "N6"):
        assert itens[nar].eh_controle
        assert itens[nar].fontes_esperadas == []


def test_golden_n1_tem_fontes_e_sql() -> None:
    item = next(i for i in carregar_golden() if i.id == "n1-recompra-sul")
    assert item.dispara_enriquecimento
    assert item.sql_esperado.upper().startswith("WITH")
    assert any("frete-gratis" in f for f in item.fontes_esperadas)
