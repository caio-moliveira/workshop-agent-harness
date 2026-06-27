"""Tool `run_sql` — leitura analítica somente-leitura sobre o schema `negocio`.

Guardrails determinísticos aplicados **ANTES** do banco (allowlist: só `SELECT`/`WITH`,
instrução única, `LIMIT` garantido) e **reforçados NO banco** (papel `agente_ro` +
`SET TRANSACTION READ ONLY` + `statement_timeout`). Nada depende do LLM (invariante:
`negocio` é SOMENTE LEITURA).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

# Palavras que denotam escrita/DDL — barradas como defesa em profundidade. O backstop real
# é o papel `agente_ro` (sem privilégio de escrita) + transação READ ONLY no banco.
_PROIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|copy|"
    r"vacuum|reindex|refresh|comment|call|into|lock|do|set)\b",
    re.IGNORECASE,
)
_COMENTARIO_LINHA = re.compile(r"--[^\n]*")
_COMENTARIO_BLOCO = re.compile(r"/\*.*?\*/", re.DOTALL)
_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")
_PRIMEIRA_PALAVRA = re.compile(r"\s*([a-zA-Z]+)")
_PONTO_VIRGULA_FINAL = re.compile(r";+\s*$")


class SQLInseguroError(ValueError):
    """SQL recusado pelos guardrails antes de tocar o banco."""


@dataclass(frozen=True)
class ResultadoSQL:
    """Resultset de uma consulta blindada (colunas + linhas) e o SQL efetivamente rodado."""

    colunas: list[str]
    # Valores de banco são heterogêneos por natureza (números, datas, texto) — Any é inevitável.
    linhas: list[dict[str, Any]]
    sql_executado: str


def _sem_comentarios(sql: str) -> str:
    """Remove comentários `--` e `/* */` para a análise não ser enganada por eles."""
    return _COMENTARIO_LINHA.sub("", _COMENTARIO_BLOCO.sub("", sql))


def validar_e_blindar_sql(sql: str, *, max_rows: int) -> str:
    """Valida o SQL contra os guardrails e devolve a versão blindada (com `LIMIT` externo).

    Levanta `SQLInseguroError` se violar qualquer invariante somente-leitura.
    """
    if not sql or not sql.strip():
        raise SQLInseguroError("SQL vazio.")

    limpo = _PONTO_VIRGULA_FINAL.sub("", _sem_comentarios(sql).strip()).strip()
    if not limpo:
        raise SQLInseguroError("SQL vazio após remover comentários.")

    # Mascarar strings evita falso-positivo de palavra-chave dentro de um literal.
    mascarado = _STRING_LITERAL.sub("''", limpo)

    if ";" in mascarado:
        raise SQLInseguroError("Apenas uma instrução é permitida (sem ';' interno).")

    inicio = _PRIMEIRA_PALAVRA.match(limpo)
    if inicio is None or inicio.group(1).lower() not in {"select", "with"}:
        raise SQLInseguroError("Só são permitidas consultas que começam com SELECT ou WITH.")

    proibida = _PROIBIDAS.search(mascarado)
    if proibida is not None:
        raise SQLInseguroError(
            f"Operação não permitida em consulta somente-leitura: {proibida.group(1)!r}."
        )

    # Envelopa SEMPRE numa subconsulta com LIMIT externo: garante o teto de linhas mesmo
    # quando o SQL traz um LIMIT só em subconsulta/CTE (que não limita o resultset externo).
    return f"SELECT * FROM (\n{limpo}\n) AS _run_sql_sub LIMIT {max_rows}"


async def run_sql(
    engine: AsyncEngine,
    sql: str,
    *,
    max_rows: int,
    statement_timeout_ms: int,
) -> ResultadoSQL:
    """Blinda o SQL e o executa como somente-leitura. `engine` deve ser o papel `agente_ro`."""
    sql_seguro = validar_e_blindar_sql(sql, max_rows=max_rows)

    async with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            # Reforço NO banco: transação só-leitura + timeout, independentes do guardrail textual.
            async with conn.begin():
                await conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                await conn.exec_driver_sql(
                    f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}"
                )
                resultado = await conn.exec_driver_sql(sql_seguro)
                colunas = list(resultado.keys())
                linhas = [dict(linha) for linha in resultado.mappings().all()]
        else:
            # Caminho de teste (SQLite): os SET são específicos do Postgres.
            resultado = await conn.exec_driver_sql(sql_seguro)
            colunas = list(resultado.keys())
            linhas = [dict(linha) for linha in resultado.mappings().all()]

    return ResultadoSQL(colunas=colunas, linhas=linhas, sql_executado=sql_seguro)
