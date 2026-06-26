"""Cria o papel SOMENTE-LEITURA agente_ro (run_sql) — SELECT apenas no schema negocio.

Revision ID: 0001_agente_ro
Revises:
Create Date: 2026-06-26

Reforço NO banco do invariante #2/#3: o agente lê via este papel, que NÃO tem
privilégio de escrita em lugar nenhum. Idempotente (pode reaplicar). A senha vem de
AGENTE_RO_PASSWORD (ambiente/.env), nunca hardcoded.

PRÉ-REQUISITO: o schema `negocio` já existe (criado por seed/load.py). Esta migration
é de infraestrutura (papel/privilégios), não cria/popula tabelas de negócio.

>>> CHECKPOINT HITL: esta migration concede privilégios — revisar à mão antes do merge. <<<
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.config import get_settings

revision: str = "0001_agente_ro"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Mesma fonte de verdade que run_sql usa (settings lê o .env) — evita papel com
    # senha divergente da que a app conecta. Sem default: falha explícita se ausente.
    senha_bruta = get_settings().agente_ro_password
    if not senha_bruta:
        raise RuntimeError(
            "AGENTE_RO_PASSWORD ausente — defina no ambiente/.env antes de aplicar a migration."
        )
    senha = senha_bruta.replace("'", "''")  # escapa aspas simples por segurança

    # Cria (ou atualiza) o papel de login, idempotente.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agente_ro') THEN
                CREATE ROLE agente_ro LOGIN PASSWORD '{senha}';
            ELSE
                ALTER ROLE agente_ro LOGIN PASSWORD '{senha}';
            END IF;
        END
        $$;
        """
    )

    # Conexão ao banco corrente (nome resolvido em runtime).
    op.execute(
        "DO $$ BEGIN "
        "EXECUTE format('GRANT CONNECT ON DATABASE %I TO agente_ro', current_database()); "
        "END $$;"
    )

    # Acesso SOMENTE-LEITURA ao schema negocio (tabelas atuais + futuras).
    op.execute("GRANT USAGE ON SCHEMA negocio TO agente_ro")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA negocio TO agente_ro")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA negocio GRANT SELECT ON TABLES TO agente_ro")

    # Hardening: nega qualquer escrita/DDL por engano (public + create no negocio).
    op.execute("REVOKE CREATE ON SCHEMA negocio FROM agente_ro")
    op.execute("REVOKE ALL ON SCHEMA public FROM agente_ro")


def downgrade() -> None:
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA negocio REVOKE SELECT ON TABLES FROM agente_ro")
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA negocio FROM agente_ro")
    op.execute("REVOKE USAGE ON SCHEMA negocio FROM agente_ro")
    op.execute(
        "DO $$ BEGIN "
        "EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM agente_ro', current_database()); "
        "END $$;"
    )
    op.execute("DROP ROLE IF EXISTS agente_ro")
