"""Entrypoint do gate de avaliação (EDD) — roda o agente sobre o golden com serviços REAIS.

Uso (precisa da stack no ar + OPENAI_API_KEY):
    uv run python evals/run_evals.py

Sai com código 0 se o veredito agregado passar o limiar, 1 caso contrário (para CI).
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, cast

from openai import OpenAI
from qdrant_client import QdrantClient

from agent.deps import Dependencias, executor_run_sql
from agent.grafo import construir_grafo
from agent.llm import criar_llm
from agent.tools.embeddings import criar_embedder
from agent.tools.run_sql import ResultadoSQL, run_sql
from agent.tools.search import ClienteQdrant
from app.config import get_settings
from app.db import criar_engine
from evals.golden import carregar_golden
from evals.juiz import JuizOpenAI
from evals.relatorio import formatar_relatorio
from evals.runner import avaliar_golden


async def _main() -> int:
    s = get_settings()
    ro_engine = criar_engine(s.agente_ro_url)
    oai = OpenAI(api_key=s.openai_api_key or "sk-absent")
    qdrant = QdrantClient(url=s.qdrant_url)

    deps = Dependencias(
        llm=criar_llm(oai, modelo_forte=s.llm_model_forte, modelo_rapido=s.llm_model_rapido),
        executar_sql=executor_run_sql(
            ro_engine, max_rows=s.max_rows, statement_timeout_ms=s.statement_timeout_ms
        ),
        qdrant=cast(ClienteQdrant, qdrant),
        embedder=criar_embedder(oai, model=s.embed_model, dim=s.embed_dim),
        hoje=s.hoje_ancora,
    )
    grafo = construir_grafo(deps)
    juiz = JuizOpenAI(oai, modelo=s.llm_model_forte)

    async def rodar_agente(pergunta: str) -> dict[str, Any]:
        return await grafo.ainvoke({"pergunta": pergunta})

    async def executar_gold(sql: str) -> ResultadoSQL:
        return await run_sql(
            ro_engine, sql, max_rows=s.max_rows, statement_timeout_ms=s.statement_timeout_ms
        )

    try:
        veredito = await avaliar_golden(
            carregar_golden(), rodar_agente=rodar_agente, executar_sql=executar_gold, juiz=juiz
        )
    finally:
        await ro_engine.dispose()

    print(formatar_relatorio(veredito))
    return 0 if veredito.passou else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
