"""Cria o schema `harness` e a tabela `runs` (rastro de execução do agente).

Revision ID: 0002_harness_runs
Revises: 0001_agente_ro
Create Date: 2026-06-27

O schema `harness` é leitura/escrita para a app (conexão admin). O papel `agente_ro`
NÃO recebe privilégio aqui — o agente só lê `negocio`. Idempotente.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_harness_runs"
down_revision: str | None = "0001_agente_ro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS harness")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS harness.runs (
            id             uuid        PRIMARY KEY,
            criado_em      timestamptz NOT NULL DEFAULT now(),
            pergunta       text        NOT NULL,
            periodo_alvo   text        NOT NULL,
            kpi_alvo       text        NOT NULL,
            dimensao       jsonb       NOT NULL,
            sql_executado  jsonb       NOT NULL,
            fontes         jsonb       NOT NULL,
            relatorio      text        NOT NULL,
            artefatos      jsonb       NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_runs_criado_em ON harness.runs (criado_em)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS harness.runs")
    op.execute("DROP SCHEMA IF EXISTS harness CASCADE")
