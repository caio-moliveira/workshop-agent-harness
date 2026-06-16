"""Persistencia do schema `harness` (issue #19): grava o que o agente fez.

Usa a conexao admin (RW). Engine com NullPool para evitar reuso entre event loops.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

_engine: AsyncEngine | None = None


def _admin_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return _engine


async def criar_run(pergunta: str, sessao_id: str | None = None) -> str:
    async with _admin_engine().begin() as conn:
        row = (
            await conn.execute(
                text(
                    "INSERT INTO harness.runs (sessao_id, pergunta, status) "
                    "VALUES (:s, :p, 'em_andamento') RETURNING id"
                ),
                {"s": sessao_id, "p": pergunta},
            )
        ).first()
    return str(row[0]) if row else ""


async def registrar_tool_call(
    run_id: str,
    ordem: int,
    tool: str,
    sql_text: str | None = None,
    resultado: Any | None = None,
) -> None:
    async with _admin_engine().begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO harness.tool_calls (run_id, ordem, tool, sql_text, resultado) "
                "VALUES (:r, :o, :t, :s, cast(:res AS jsonb))"
            ),
            {
                "r": run_id,
                "o": ordem,
                "t": tool,
                "s": sql_text,
                "res": json.dumps(resultado) if resultado is not None else None,
            },
        )


async def finalizar_run(run_id: str, relatorio: str, status: str = "concluido") -> None:
    async with _admin_engine().begin() as conn:
        await conn.execute(
            text("UPDATE harness.runs SET relatorio = :rel, status = :st WHERE id = :id"),
            {"rel": relatorio, "st": status, "id": run_id},
        )
