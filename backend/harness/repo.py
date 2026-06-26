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
