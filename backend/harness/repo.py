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


async def criar_sessao(rotulo: str | None = None) -> str:
    async with _admin_engine().begin() as conn:
        row = (
            await conn.execute(
                text("INSERT INTO harness.sessoes (rotulo) VALUES (:r) RETURNING id"),
                {"r": rotulo},
            )
        ).first()
    return str(row[0]) if row else ""


async def criar_run(
    pergunta: str,
    sessao_id: str | None = None,
    pergunta_reescrita: str | None = None,
) -> str:
    async with _admin_engine().begin() as conn:
        row = (
            await conn.execute(
                text(
                    "INSERT INTO harness.runs (sessao_id, pergunta, pergunta_reescrita, status) "
                    "VALUES (:s, :p, :pr, 'em_andamento') RETURNING id"
                ),
                {"s": sessao_id, "p": pergunta, "pr": pergunta_reescrita},
            )
        ).first()
    return str(row[0]) if row else ""


async def historico_sessao(sessao_id: str, limite: int = 5) -> list[dict[str, Any]]:
    """Turnos concluidos da sessao, mais recente primeiro (para o condense-question)."""
    async with _admin_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT pergunta, pergunta_reescrita, relatorio FROM harness.runs "
                    "WHERE sessao_id = :s AND status = 'concluido' "
                    "ORDER BY criado_em DESC LIMIT :n"
                ),
                {"s": sessao_id, "n": limite},
            )
        ).all()
    return [
        {"pergunta": r[0], "pergunta_reescrita": r[1], "relatorio": r[2]} for r in rows
    ]


async def fontes_prescricao_da_sessao(sessao_id: str) -> list[str]:
    """Fontes de prescricao ja recuperadas na sessao — para nao repetir recomendacoes."""
    async with _admin_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT DISTINCT fr.fonte FROM harness.fontes_recuperadas fr "
                    "JOIN harness.runs r ON fr.run_id = r.id "
                    "WHERE r.sessao_id = :s AND fr.colecao = 'prescricao' "
                    "AND fr.fonte IS NOT NULL"
                ),
                {"s": sessao_id},
            )
        ).all()
    return [r[0] for r in rows]


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


async def registrar_fonte(
    run_id: str,
    colecao: str,
    fonte: str | None = None,
    payload: Any | None = None,
    score: float | None = None,
) -> None:
    async with _admin_engine().begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO harness.fontes_recuperadas (run_id, colecao, fonte, payload, score) "
                "VALUES (:r, :c, :f, cast(:p AS jsonb), :s)"
            ),
            {
                "r": run_id,
                "c": colecao,
                "f": fonte,
                "p": json.dumps(payload) if payload is not None else None,
                "s": score,
            },
        )


async def finalizar_run(run_id: str, relatorio: str, status: str = "concluido") -> None:
    async with _admin_engine().begin() as conn:
        await conn.execute(
            text("UPDATE harness.runs SET relatorio = :rel, status = :st WHERE id = :id"),
            {"rel": relatorio, "st": status, "id": run_id},
        )
