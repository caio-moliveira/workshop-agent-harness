"""Runner do eval: roda o grafo do agente em cada caso do golden e pontua o resultado.

Coleta o que o agente REALMENTE fez (fontes recuperadas, SQL rodado, dados, relatório) e
aplica as métricas puras (`scoring`) + o judge (faithfulness). Produz um relatório
inspecionável (por caso + agregado) — é o trace que o analista lê para entender o baseline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from evals.golden import CasoGolden
from evals.judge import Juiz
from evals.scoring import Agregado, PontuacaoCaso, agregar, pontuar_caso


@dataclass(frozen=True)
class ResultadoCaso:
    """Resultado por caso — tudo que sustenta o número (inspecionável)."""

    id: str
    narrativa: str
    intencao: str
    enriqueceu: bool
    esperava_enriquecer: bool
    fontes_recuperadas: list[str]
    pontuacao: PontuacaoCaso
    faithfulness: float
    justificativa_juiz: str
    relatorio: str


@dataclass(frozen=True)
class RelatorioEval:
    """O eval inteiro: casos + agregado."""

    casos: list[ResultadoCaso]
    agregado: Agregado

    def como_dict(self) -> dict[str, Any]:
        """Serializa para JSON (report inspecionável gravado em disco)."""
        return {
            "agregado": asdict(self.agregado),
            "casos": [{**asdict(c), "pontuacao": asdict(c.pontuacao)} for c in self.casos],
        }


def _caso_falho(caso: CasoGolden, erro: str) -> ResultadoCaso:
    """Caso que estourou no grafo é uma FALHA MEDIDA (não aborta o eval): zera os sinais."""
    pontuacao = pontuar_caso(
        esperado_enriquece=caso.dispara_enriquecimento,
        fontes_esperadas=caso.fontes_esperadas,
        distratores=caso.distratores,
        fontes_recuperadas=[],
        rodou_sql=False,
        dados_nao_vazios=False,
    )
    return ResultadoCaso(
        id=caso.id,
        narrativa=caso.narrativa,
        intencao=caso.intencao,
        enriqueceu=False,
        esperava_enriquecer=caso.dispara_enriquecimento,
        fontes_recuperadas=[],
        pontuacao=pontuacao,
        faithfulness=0.0,
        justificativa_juiz=f"caso falhou no grafo: {erro}",
        relatorio="",
    )


async def _rodar_caso(caso: CasoGolden, *, grafo: Any, juiz: Juiz) -> ResultadoCaso:
    """Executa um caso: roda o grafo, coleta o real e pontua (determinístico + judge).

    Todo o caminho (grafo + parsing + judge) está sob try: qualquer estouro — inclusive um
    timeout de API do juiz — vira falha medida, nunca aborta o eval inteiro.
    """
    config = {"configurable": {"thread_id": f"eval-{caso.id}"}}
    try:
        estado = await grafo.ainvoke({"pergunta": caso.pergunta}, config)

        fontes = list(estado.get("fontes", []))
        sqls = list(estado.get("sql_executado", []))
        dados = estado.get("dados", {})
        relatorio = str(estado.get("relatorio", ""))
        dados_nao_vazios = any(len(linhas) > 0 for linhas in dados.values())

        pontuacao = pontuar_caso(
            esperado_enriquece=caso.dispara_enriquecimento,
            fontes_esperadas=caso.fontes_esperadas,
            distratores=caso.distratores,
            fontes_recuperadas=fontes,
            rodou_sql=len(sqls) > 0,
            dados_nao_vazios=dados_nao_vazios,
        )
        veredicto = await juiz.avaliar(
            recomendacao_esperada=caso.recomendacao_esperada, relatorio=relatorio
        )
    except Exception as exc:  # noqa: BLE001 — caso que estoura (grafo/judge) vira falha medida
        return _caso_falho(caso, type(exc).__name__)

    return ResultadoCaso(
        id=caso.id,
        narrativa=caso.narrativa,
        intencao=caso.intencao,
        enriqueceu=len(fontes) > 0,
        esperava_enriquecer=caso.dispara_enriquecimento,
        fontes_recuperadas=fontes,
        pontuacao=pontuacao,
        faithfulness=veredicto.score,
        justificativa_juiz=veredicto.justificativa,
        relatorio=relatorio,
    )


async def rodar_eval(casos: list[CasoGolden], *, grafo: Any, juiz: Juiz) -> RelatorioEval:
    """Roda todos os casos (em sequência — determinismo e logs legíveis) e agrega."""
    resultados: list[ResultadoCaso] = []
    for caso in casos:
        resultados.append(await _rodar_caso(caso, grafo=grafo, juiz=juiz))
    agg = agregar(
        [r.pontuacao for r in resultados],
        faithfulness=[r.faithfulness for r in resultados],
    )
    return RelatorioEval(casos=resultados, agregado=agg)
