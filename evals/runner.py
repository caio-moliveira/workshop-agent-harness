"""Orquestra a avaliação de cada item do golden. Dependências injetadas (grafo, executor
de SQL, juiz) — o entrypoint passa as reais; testes passam fakes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from agent.tools.run_sql import ResultadoSQL
from evals.comparadores import avaliar_grounding, resultset_nao_vazio, routing_ok
from evals.golden import ItemGolden
from evals.juiz import Juiz
from evals.relatorio import Limiares, ResultadoItem, Veredito

# Roda uma pergunta no agente e devolve o estado final do grafo.
RodarAgente = Callable[[str], Awaitable[dict[str, Any]]]
# Executa um SQL (o gold) e devolve o resultset.
ExecutarSQL = Callable[[str], Awaitable[ResultadoSQL]]


async def avaliar_item(
    item: ItemGolden, *, rodar_agente: RodarAgente, executar_sql: ExecutarSQL, juiz: Juiz
) -> ResultadoItem:
    """Roda o agente e o gold, computa os sinais. Robusto: erro do item não derruba o lote."""
    try:
        estado = await rodar_agente(item.pergunta)
        fontes: list[str] = estado.get("fontes", [])
        disparou = len(fontes) > 0
        dados: dict[str, list[dict[str, Any]]] = estado.get("dados", {})
        exec_agente = any(resultset_nao_vazio(linhas) for linhas in dados.values())

        gold = await executar_sql(item.sql_esperado)
        exec_golden = resultset_nao_vazio(gold.linhas)

        resultado = ResultadoItem(
            id=item.id,
            eh_controle=item.eh_controle,
            exec_golden_ok=exec_golden,
            exec_agente_ok=exec_agente,
            routing_ok=routing_ok(disparou, item.dispara_enriquecimento),
        )
        if not item.eh_controle:
            resultado.grounding = avaliar_grounding(
                fontes, item.fontes_esperadas, item.distratores
            )
            resultado.nota = await juiz.avaliar(
                pergunta=item.pergunta,
                recomendacao_obtida=estado.get("relatorio", ""),
                recomendacao_esperada=item.recomendacao_esperada,
            )
        return resultado
    except Exception as exc:  # noqa: BLE001 — falha de um item vira FAIL, não derruba o eval
        return ResultadoItem(
            id=item.id, eh_controle=item.eh_controle, erro=f"{type(exc).__name__}: {exc}"
        )


async def avaliar_golden(
    itens: Sequence[ItemGolden],
    *,
    rodar_agente: RodarAgente,
    executar_sql: ExecutarSQL,
    juiz: Juiz,
    limiares: Limiares | None = None,
) -> Veredito:
    """Avalia todos os itens (sequencial) e agrega no veredito."""
    veredito = Veredito(limiares=limiares or Limiares())
    for item in itens:
        veredito.itens.append(
            await avaliar_item(
                item, rodar_agente=rodar_agente, executar_sql=executar_sql, juiz=juiz
            )
        )
    return veredito
