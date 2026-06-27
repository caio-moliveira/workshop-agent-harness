from __future__ import annotations

from typing import Any

from evals.golden import CasoGolden
from evals.judge import VeredictoJuiz
from evals.runner import rodar_eval


class FakeGrafo:
    """Grafo fake: devolve um estado canned por pergunta (sem LLM/stores reais)."""

    def __init__(self, estados: dict[str, dict[str, Any]]) -> None:
        self._estados = estados

    async def ainvoke(self, entrada: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return self._estados[entrada["pergunta"]]


class FakeJuiz:
    async def avaliar(self, *, recomendacao_esperada: str, relatorio: str) -> VeredictoJuiz:
        # Score determinístico: 1.0 se o relatório não for vazio.
        return VeredictoJuiz(score=1.0 if relatorio else 0.0, justificativa="fake")


def _caso(cid: str, enriquece: bool, fontes: list[str], distr: list[str]) -> CasoGolden:
    return CasoGolden(
        id=cid,
        narrativa=cid,
        intencao="central",
        dispara_enriquecimento=enriquece,
        pergunta=f"p-{cid}",
        sql_esperado="SELECT 1",
        fontes_esperadas=fontes,
        distratores=distr,
        recomendacao_esperada="ref",
    )


async def test_runner_pontua_caso_central_e_controle() -> None:
    """Central com fontes certas + controle sem enriquecer → roteamento 2/2, recall cheio."""
    central = _caso("n1", True, ["minio://a.md", "minio://b.md"], ["minio://d.md"])
    controle = _caso("n4", False, [], [])
    estados = {
        "p-n1": {
            "fontes": ["minio://a.md", "minio://b.md"],
            "sql_executado": ["SELECT 1"],
            "dados": {"tendencia": [{"v": 1}]},
            "relatorio": "## Diagnóstico ...",
        },
        "p-n4": {
            "fontes": [],
            "sql_executado": ["SELECT 1"],
            "dados": {"tendencia": [{"v": 1}]},
            "relatorio": "## KPI saudável",
        },
    }
    rel = await rodar_eval([central, controle], grafo=FakeGrafo(estados), juiz=FakeJuiz())

    assert rel.agregado.n_casos == 2
    assert rel.agregado.roteamento_ok == 2  # central enriqueceu, controle não
    assert rel.agregado.recall_medio == 1.0
    assert rel.agregado.casos_sem_distrator == 2
    assert rel.agregado.execucao_ok == 2
    assert rel.agregado.faithfulness_media == 1.0


async def test_runner_detecta_distrator_e_recall_parcial() -> None:
    """Recupera 1 de 2 esperadas + 1 distrator → recall 0.5, precisão furada."""
    central = _caso("n1", True, ["minio://a.md", "minio://b.md"], ["minio://d.md"])
    estados = {
        "p-n1": {
            "fontes": ["minio://a.md", "minio://d.md"],
            "sql_executado": ["SELECT 1"],
            "dados": {"tendencia": [{"v": 1}]},
            "relatorio": "rel",
        }
    }
    rel = await rodar_eval([central], grafo=FakeGrafo(estados), juiz=FakeJuiz())
    c = rel.casos[0]
    assert c.pontuacao.recall_fontes == 0.5
    assert c.pontuacao.distratores_citados == 1
    assert c.pontuacao.precisao_ok is False


class GrafoQueEstoura:
    async def ainvoke(self, entrada: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("template não suportado")


async def test_runner_caso_que_estoura_vira_falha_medida() -> None:
    """Um caso que estoura no grafo não aborta o eval — vira falha (execução X), eval segue."""
    central = _caso("n2", True, ["minio://a.md"], [])
    rel = await rodar_eval([central], grafo=GrafoQueEstoura(), juiz=FakeJuiz())
    c = rel.casos[0]
    assert c.pontuacao.execucao_ok is False
    assert c.pontuacao.recall_fontes == 0.0
    assert c.faithfulness == 0.0
    assert "falhou no grafo" in c.justificativa_juiz
    assert rel.agregado.n_casos == 1  # o eval completou apesar da falha


async def test_runner_controle_que_enriquece_erra_roteamento() -> None:
    """Controle que enriquece indevidamente → roteamento errado."""
    controle = _caso("n6", False, [], [])
    estados = {
        "p-n6": {
            "fontes": ["minio://x.md"],
            "sql_executado": ["SELECT 1"],
            "dados": {"tendencia": [{"v": 1}]},
            "relatorio": "rel",
        }
    }
    rel = await rodar_eval([controle], grafo=FakeGrafo(estados), juiz=FakeJuiz())
    assert rel.casos[0].pontuacao.roteamento_ok is False
