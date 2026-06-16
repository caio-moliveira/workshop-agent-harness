"""Testes da tool run_sql (issue #17).

Guardrails deterministicos sao testados sem banco; execucao read-only e
statement_timeout em testes de integracao que pulam se o Postgres/role estiver
indisponivel.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from agent.tools.run_sql import (
    SQLGuardrailError,
    enforce_read_only,
    ensure_limit,
    run_sql,
)
from app.config import settings

# ---- Guardrails deterministicos (sem banco) ----


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO negocio.regioes VALUES (9, 'x')",
        "UPDATE negocio.regioes SET nome = 'x'",
        "DELETE FROM negocio.regioes",
        "DROP TABLE negocio.regioes",
        "TRUNCATE negocio.regioes",
        "ALTER TABLE negocio.regioes ADD COLUMN x integer",
    ],
)
def test_enforce_read_only_rejeita_escrita(sql: str) -> None:
    with pytest.raises(SQLGuardrailError):
        enforce_read_only(sql)


def test_enforce_read_only_rejeita_multiplas_instrucoes() -> None:
    with pytest.raises(SQLGuardrailError):
        enforce_read_only("SELECT 1; DROP TABLE negocio.regioes")


def test_enforce_read_only_aceita_select_e_with() -> None:
    assert enforce_read_only("SELECT 1").lower().startswith("select")
    assert (
        enforce_read_only("WITH t AS (SELECT 1) SELECT * FROM t").lower().startswith("with")
    )


def test_ensure_limit_injeta_quando_ausente() -> None:
    assert "LIMIT 10" in ensure_limit("SELECT * FROM negocio.regioes", max_rows=10)


def test_ensure_limit_preserva_quando_presente() -> None:
    out = ensure_limit("SELECT * FROM negocio.regioes LIMIT 5", max_rows=10)
    assert out.count("LIMIT") == 1
    assert "LIMIT 5" in out


# ---- Integracao (skip se Postgres/role indisponivel) ----


async def _ro_indisponivel() -> bool:
    if not settings.agente_ro_password:
        return True
    engine = create_async_engine(settings.agente_ro_url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return False
    except Exception:
        return True
    finally:
        await engine.dispose()


async def test_run_sql_select_retorna_linhas() -> None:
    if await _ro_indisponivel():
        pytest.skip("Postgres/role read-only indisponivel")
    res = await run_sql("SELECT id, nome FROM negocio.regioes")
    assert res.rowcount > 0
    assert "nome" in res.columns
    assert "LIMIT" in res.sql  # LIMIT injetado pelo guardrail


async def test_run_sql_escrita_barrada_antes_do_banco() -> None:
    # Guardrail levanta antes de qualquer conexao.
    with pytest.raises(SQLGuardrailError):
        await run_sql("INSERT INTO negocio.regioes VALUES (9, 'x')")


async def test_run_sql_respeita_statement_timeout() -> None:
    if await _ro_indisponivel():
        pytest.skip("Postgres/role read-only indisponivel")
    with pytest.raises(DBAPIError):
        await run_sql("SELECT pg_sleep(2)", timeout_ms=100)
