from __future__ import annotations

from typing import Any

from agent.tools.run_sql import ResultadoSQL
from evals.golden import ItemGolden
from evals.juiz import NotaJuiz
from evals.relatorio import Limiares, formatar_relatorio
from evals.runner import avaliar_golden


class FakeJuiz:
    def __init__(self, nota: NotaJuiz) -> None:
        self._nota = nota

    async def avaliar(self, **kwargs: Any) -> NotaJuiz:
        return self._nota


def _gold_exec(_sql: str):
    async def _exec(_s: str) -> ResultadoSQL:
        return ResultadoSQL(colunas=["n"], linhas=[{"n": 1}], sql_executado=_s)

    return _exec


def _item(id_: str, *, controle: bool, fontes: list[str], distratores: list[str]) -> ItemGolden:
    return ItemGolden(
        id=id_,
        narrativa=id_,
        intencao="x",
        dispara_enriquecimento=not controle,
        pergunta="p?",
        sql_esperado="SELECT 1",
        fontes_esperadas=fontes,
        distratores=distratores,
        recomendacao_esperada="esperado",
    )


async def test_item_enriquecimento_passa_com_grounding_e_juiz_altos() -> None:
    item = _item("n1", controle=False, fontes=["minio://a"], distratores=["minio://x"])

    async def rodar(_p: str) -> dict[str, Any]:
        return {"fontes": ["minio://a"], "dados": {"tendencia": [{"v": 1}]}, "relatorio": "rec"}

    veredito = await avaliar_golden(
        [item],
        rodar_agente=rodar,
        executar_sql=_gold_exec("x"),
        juiz=FakeJuiz(NotaJuiz(0.9, 0.9)),
    )
    assert veredito.itens[0].passou(veredito.limiares)
    assert veredito.passou


async def test_item_reprova_se_cita_distrator() -> None:
    item = _item("n1", controle=False, fontes=["minio://a"], distratores=["minio://x"])

    async def rodar(_p: str) -> dict[str, Any]:
        return {"fontes": ["minio://a", "minio://x"], "dados": {"t": [{"v": 1}]}, "relatorio": "r"}

    veredito = await avaliar_golden(
        [item],
        rodar_agente=rodar,
        executar_sql=_gold_exec("x"),
        juiz=FakeJuiz(NotaJuiz(0.9, 0.9)),
    )
    assert not veredito.itens[0].passou(veredito.limiares)  # distrator citado


async def test_controle_passa_se_nao_enriquece() -> None:
    item = _item("n6", controle=True, fontes=[], distratores=[])

    async def rodar(_p: str) -> dict[str, Any]:
        return {"fontes": [], "dados": {"t": [{"v": 1}]}, "relatorio": "r"}

    veredito = await avaliar_golden(
        [item], rodar_agente=rodar, executar_sql=_gold_exec("x"), juiz=FakeJuiz(NotaJuiz(0, 0))
    )
    assert veredito.itens[0].passou(veredito.limiares)


async def test_controle_reprova_se_enriquece_indevidamente() -> None:
    item = _item("n4", controle=True, fontes=[], distratores=[])

    async def rodar(_p: str) -> dict[str, Any]:
        return {"fontes": ["minio://a"], "dados": {"t": [{"v": 1}]}, "relatorio": "r"}

    veredito = await avaliar_golden(
        [item], rodar_agente=rodar, executar_sql=_gold_exec("x"), juiz=FakeJuiz(NotaJuiz(0, 0))
    )
    assert not veredito.itens[0].passou(veredito.limiares)  # routing errado


async def test_erro_no_item_vira_fail_sem_derrubar_o_lote() -> None:
    item = _item("n2", controle=False, fontes=["minio://a"], distratores=[])

    async def rodar(_p: str) -> dict[str, Any]:
        raise RuntimeError("template não suportado")

    veredito = await avaliar_golden(
        [item], rodar_agente=rodar, executar_sql=_gold_exec("x"), juiz=FakeJuiz(NotaJuiz(1, 1))
    )
    assert veredito.itens[0].erro is not None
    assert not veredito.itens[0].passou(veredito.limiares)
    assert "FAIL" in formatar_relatorio(veredito)


async def test_taxa_aprovacao_define_veredito_agregado() -> None:
    """4 controles ok + 1 controle que enriquece (FAIL) = 80% -> passa no limiar 0.8."""
    bons = [_item(f"ok{i}", controle=True, fontes=[], distratores=[]) for i in range(4)]
    ruim = _item("ruim", controle=True, fontes=[], distratores=[])
    object.__setattr__(ruim, "pergunta", "ENRIQUECE")  # distingue o item que enriquece
    itens = bons + [ruim]

    async def rodar(pergunta: str) -> dict[str, Any]:
        fontes = ["minio://a"] if pergunta == "ENRIQUECE" else []
        return {"fontes": fontes, "dados": {"t": [{"v": 1}]}, "relatorio": "r"}

    veredito = await avaliar_golden(
        itens,
        rodar_agente=rodar,
        executar_sql=_gold_exec("x"),
        juiz=FakeJuiz(NotaJuiz(1, 1)),
        limiares=Limiares(taxa_aprovacao=0.8),
    )
    assert veredito.aprovados == 4
    assert veredito.taxa == 0.8
    assert veredito.passou  # exatamente no limiar
