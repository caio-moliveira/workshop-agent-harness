"""Tool run_sql: SQL somente-leitura contra `negocio`, com guardrails deterministicos.

Os guardrails sao aplicados ANTES de tocar o banco (allowlist de comando + instrucao
unica + LIMIT) e reforcados NO banco (papel read-only + transacao READ ONLY +
statement_timeout). Nada disso depende do LLM. Reutilizada pelos nos do grafo (#19+).

Usa NullPool: cada chamada abre uma conexao curta. Evita reuso de conexao entre
event loops (seguro sob pytest-asyncio) e mantem a tool simples para queries pontuais.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

DEFAULT_MAX_ROWS = 1000
DEFAULT_TIMEOUT_MS = 5000


class SQLGuardrailError(ValueError):
    """SQL rejeitado por um guardrail deterministico, antes de tocar o banco."""


@dataclass
class SqlResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]
    rowcount: int
    sql: str  # SQL efetivamente executado (com LIMIT garantido)


_engine: AsyncEngine | None = None


def _get_ro_engine() -> AsyncEngine:
    """Engine async com o papel read-only (agente_ro). Singleton, sem pool de conexoes."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.agente_ro_url, poolclass=NullPool)
    return _engine


def _strip_comments(sql: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    no_line = re.sub(r"--[^\n]*", " ", no_block)
    return no_line.strip()


def enforce_read_only(sql: str) -> str:
    """Valida: uma unica instrucao SELECT/WITH. Levanta SQLGuardrailError caso contrario."""
    cleaned = _strip_comments(sql)
    if not cleaned:
        raise SQLGuardrailError("SQL vazio")
    statements = [s for s in cleaned.rstrip(";").split(";") if s.strip()]
    if len(statements) != 1:
        raise SQLGuardrailError("apenas uma instrucao e permitida por chamada")
    stmt = statements[0].strip()
    if re.match(r"^(select|with)\b", stmt, flags=re.IGNORECASE) is None:
        raise SQLGuardrailError("apenas consultas SELECT/WITH sao permitidas")
    return stmt


def ensure_limit(sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> str:
    """Garante um LIMIT; injeta `LIMIT max_rows` se ausente."""
    if re.search(r"\blimit\s+\d+", sql, flags=re.IGNORECASE) is not None:
        return sql
    return f"{sql}\nLIMIT {int(max_rows)}"


async def run_sql(
    sql: str,
    *,
    max_rows: int = DEFAULT_MAX_ROWS,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> SqlResult:
    """Executa uma consulta read-only em `negocio` com todos os guardrails aplicados."""
    stmt = enforce_read_only(sql)
    guarded = ensure_limit(stmt, max_rows)
    engine = _get_ro_engine()
    async with engine.connect() as conn, conn.begin():
        await conn.execute(text("SET TRANSACTION READ ONLY"))
        await conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result = await conn.execute(text(guarded))
        columns = [str(c) for c in result.keys()]
        fetched = result.fetchall()
    rows = [tuple(row) for row in fetched]
    return SqlResult(columns=columns, rows=rows, rowcount=len(rows), sql=guarded)
