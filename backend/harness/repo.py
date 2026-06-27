"""Persistência de runs no schema `harness` — parte do contrato, não opcional (`backend.md`).

Usa a conexão ADMIN (RW), nunca o papel `agente_ro`. O agente lê `negocio`; quem escreve
o rastro de execução é a app.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from harness.modelo import RUNS, RegistroRun


async def gravar_run(engine: AsyncEngine, registro: RegistroRun, *, tabela: sa.Table = RUNS) -> str:
    """Insere o run e devolve seu id. `tabela` é injetável (teste usa SQLite sem schema)."""
    async with engine.begin() as conn:
        await conn.execute(sa.insert(tabela).values(**registro.como_linha()))
    return registro.id


async def fontes_recomendadas_da_thread(
    engine: AsyncEngine, thread_id: str, *, tabela: sa.Table = RUNS
) -> set[str]:
    """Fontes citadas em runs anteriores desta conversa — para não repetir recomendações.

    Fonte durável (sobrevive a restart, ao contrário do checkpointer em memória). Lê a coluna
    `fontes` (diagnóstico + prescrição), mais ampla que só as recomendadas — seguro porque as
    URIs de `diagnostico` e `prescricao` vivem em paths MinIO disjuntos, então nunca colidem.
    """
    async with engine.connect() as conn:
        linhas = (
            (await conn.execute(sa.select(tabela.c.fontes).where(tabela.c.thread_id == thread_id)))
            .scalars()
            .all()
        )
    fontes: set[str] = set()
    for lista in linhas:
        if lista:
            fontes.update(lista)
    return fontes
