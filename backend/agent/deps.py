"""Dependências injetadas no grafo — fecham sobre os nós (closures), o que mantém o
grafo testável (passa-se fakes em teste) e sem estado global."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncEngine

from agent.llm import ModeloLLM
from agent.tools.embeddings import Embedder
from agent.tools.run_sql import ResultadoSQL, run_sql
from agent.tools.search import ClienteQdrant

# Executor de SQL injetável: recebe o SQL e devolve o resultset blindado. Produção embrulha
# `run_sql` (guardrails + papel RO); teste passa um fake (sem Postgres).
ExecutorSQL = Callable[[str], Awaitable[ResultadoSQL]]


@dataclass(frozen=True)
class Dependencias:
    """Tudo que os nós precisam do mundo externo — uma só superfície de injeção."""

    llm: ModeloLLM
    executar_sql: ExecutorSQL
    qdrant: ClienteQdrant
    embedder: Embedder
    hoje: date


def executor_run_sql(
    engine: AsyncEngine, *, max_rows: int, statement_timeout_ms: int
) -> ExecutorSQL:
    """Constrói o executor de produção: cada SQL passa pelos guardrails do `run_sql` (papel RO)."""

    async def _executar(sql: str) -> ResultadoSQL:
        return await run_sql(
            engine, sql, max_rows=max_rows, statement_timeout_ms=statement_timeout_ms
        )

    return _executar
