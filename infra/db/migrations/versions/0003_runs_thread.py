"""Adiciona `thread_id` a harness.runs (conversa multi-turno).

Revision ID: 0003_runs_thread
Revises: 0002_harness_runs
Create Date: 2026-06-27

Agrupa os runs de uma mesma linha de conversa (thread) para o agente não repetir
recomendações já dadas. Idempotente.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_runs_thread"
down_revision: str | None = "0002_harness_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE harness.runs ADD COLUMN IF NOT EXISTS thread_id uuid")
    op.execute("CREATE INDEX IF NOT EXISTS ix_runs_thread ON harness.runs (thread_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS harness.ix_runs_thread")
    op.execute("ALTER TABLE harness.runs DROP COLUMN IF EXISTS thread_id")
