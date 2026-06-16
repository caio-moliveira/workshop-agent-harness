"""harness schema + role read-only do agente (issue #16)

Cria o schema `harness` (sessoes, runs, tool_calls, fontes_recuperadas, traces) e
o role read-only do agente (run_sql), com SELECT somente em `negocio` e nenhum
privilegio de escrita. Idempotente: pode rodar com ou sem o schema `negocio`
ainda populado.

Revision ID: 0001_harness
Revises:
Create Date: 2026-06-16
"""

import os

from alembic import op

revision = "0001_harness"
down_revision = None
branch_labels = None
depends_on = None

_RO_USER = os.environ.get("AGENTE_RO_USER", "agente_ro")
# Escapa aspa simples para o literal SQL do CREATE ROLE.
_RO_PASSWORD = os.environ.get("AGENTE_RO_PASSWORD", "agente_ro").replace("'", "''")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS harness")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS harness.sessoes (
            id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            rotulo    text,
            criado_em timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS harness.runs (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            sessao_id          uuid REFERENCES harness.sessoes(id) ON DELETE CASCADE,
            pergunta           text NOT NULL,
            pergunta_reescrita text,
            relatorio          text,
            status             text NOT NULL DEFAULT 'em_andamento',
            langfuse_trace_id  text,
            criado_em          timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS harness.tool_calls (
            id        bigserial PRIMARY KEY,
            run_id    uuid NOT NULL REFERENCES harness.runs(id) ON DELETE CASCADE,
            ordem     integer NOT NULL,
            tool      text NOT NULL,
            args      jsonb,
            sql_text  text,
            resultado jsonb,
            criado_em timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS harness.fontes_recuperadas (
            id        bigserial PRIMARY KEY,
            run_id    uuid NOT NULL REFERENCES harness.runs(id) ON DELETE CASCADE,
            colecao   text NOT NULL,
            fonte     text,
            payload   jsonb,
            score     double precision,
            criado_em timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS harness.traces (
            id        bigserial PRIMARY KEY,
            run_id    uuid REFERENCES harness.runs(id) ON DELETE CASCADE,
            evento    text NOT NULL,
            dados     jsonb,
            criado_em timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    # Role read-only do agente (run_sql). Idempotente.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_RO_USER}') THEN
                CREATE ROLE {_RO_USER} LOGIN PASSWORD '{_RO_PASSWORD}';
            END IF;
        END $$;
        """
    )
    # So leitura em negocio; nenhum privilegio de escrita. Guardado por existencia do schema.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'negocio') THEN
                GRANT USAGE ON SCHEMA negocio TO {_RO_USER};
                GRANT SELECT ON ALL TABLES IN SCHEMA negocio TO {_RO_USER};
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA negocio '
                        'GRANT SELECT ON TABLES TO {_RO_USER}';
            END IF;
        END $$;
        """
    )
    # Garante que o role nao acessa o schema harness (RW exclusivo do app).
    op.execute(f"REVOKE ALL ON SCHEMA harness FROM {_RO_USER}")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS harness CASCADE")
    # O role nao e dropado automaticamente (pode estar em uso por conexoes ativas).
