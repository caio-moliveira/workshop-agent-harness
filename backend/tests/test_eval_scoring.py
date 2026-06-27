from __future__ import annotations

from evals.scoring import (
    acerto_roteamento,
    agregar,
    conta_distratores,
    pontuar_caso,
    recall_fontes,
)


def test_roteamento_enriquece_quando_esperado() -> None:
    assert acerto_roteamento(True, ["minio://a.md"]) is True
    assert acerto_roteamento(True, []) is False  # devia enriquecer e não enriqueceu


def test_roteamento_controle_nao_enriquece() -> None:
    """Controle (n4/n6): acerto = nenhuma fonte recuperada."""
    assert acerto_roteamento(False, []) is True
    assert acerto_roteamento(False, ["minio://x.md"]) is False  # enriqueceu indevidamente


def test_recall_fontes() -> None:
    esperadas = ["a", "b", "c", "d"]
    assert recall_fontes(esperadas, ["a", "b", "x"]) == 0.5
    assert recall_fontes(esperadas, ["a", "b", "c", "d"]) == 1.0
    assert recall_fontes(esperadas, []) == 0.0


def test_recall_sem_esperadas_eh_um() -> None:
    """Caso de controle não tem fontes esperadas — recall trivialmente 1.0."""
    assert recall_fontes([], ["qualquer"]) == 1.0


def test_conta_distratores() -> None:
    distratores = ["d1", "d2"]
    assert conta_distratores(distratores, ["a", "d1"]) == 1
    assert conta_distratores(distratores, ["d1", "d2"]) == 2
    assert conta_distratores(distratores, ["a", "b"]) == 0


def test_pontuar_caso_central_perfeito() -> None:
    p = pontuar_caso(
        esperado_enriquece=True,
        fontes_esperadas=["a", "b"],
        distratores=["d"],
        fontes_recuperadas=["a", "b"],
        rodou_sql=True,
        dados_nao_vazios=True,
    )
    assert p.roteamento_ok and p.recall_fontes == 1.0 and p.precisao_ok and p.execucao_ok


def test_pontuar_caso_distrator_derruba_precisao() -> None:
    p = pontuar_caso(
        esperado_enriquece=True,
        fontes_esperadas=["a"],
        distratores=["d"],
        fontes_recuperadas=["a", "d"],
        rodou_sql=True,
        dados_nao_vazios=True,
    )
    assert p.recall_fontes == 1.0
    assert p.distratores_citados == 1
    assert p.precisao_ok is False


def test_execucao_exige_sql_e_dados() -> None:
    def pontua(rodou_sql: bool, dados_nao_vazios: bool) -> bool:
        return pontuar_caso(
            esperado_enriquece=False,
            fontes_esperadas=[],
            distratores=[],
            fontes_recuperadas=[],
            rodou_sql=rodou_sql,
            dados_nao_vazios=dados_nao_vazios,
        ).execucao_ok

    assert pontua(True, True) is True
    assert pontua(True, False) is False
    assert pontua(False, True) is False


def test_agregar_resume_casos() -> None:
    p1 = pontuar_caso(
        esperado_enriquece=True,
        fontes_esperadas=["a", "b"],
        distratores=[],
        fontes_recuperadas=["a", "b"],
        rodou_sql=True,
        dados_nao_vazios=True,
    )
    p2 = pontuar_caso(
        esperado_enriquece=True,
        fontes_esperadas=["a", "b"],
        distratores=["d"],
        fontes_recuperadas=["a", "d"],
        rodou_sql=True,
        dados_nao_vazios=True,
    )
    ag = agregar([p1, p2], faithfulness=[1.0, 0.0])
    assert ag.n_casos == 2
    assert ag.roteamento_ok == 2
    assert ag.recall_medio == 0.75  # (1.0 + 0.5) / 2
    assert ag.recall_medio_central == 0.75  # ambos enriquecem -> igual ao global aqui
    assert ag.casos_sem_distrator == 1
    assert ag.execucao_ok == 2
    assert ag.faithfulness_media == 0.5


def test_recall_central_ignora_controles() -> None:
    """Controle (recall trivial 1.0) não infla o recall central — só casos que enriquecem."""
    central = pontuar_caso(
        esperado_enriquece=True,
        fontes_esperadas=["a", "b"],
        distratores=[],
        fontes_recuperadas=["a"],
        rodou_sql=True,
        dados_nao_vazios=True,
    )  # recall 0.5
    controle = pontuar_caso(
        esperado_enriquece=False,
        fontes_esperadas=[],
        distratores=[],
        fontes_recuperadas=[],
        rodou_sql=True,
        dados_nao_vazios=True,
    )  # recall trivial 1.0
    ag = agregar([central, controle])
    assert ag.recall_medio == 0.75  # global mistura (0.5 + 1.0) / 2
    assert ag.recall_medio_central == 0.5  # central só conta o caso que enriquece


def test_agregar_vazio_nao_quebra() -> None:
    ag = agregar([])
    assert ag.n_casos == 0 and ag.faithfulness_media is None
