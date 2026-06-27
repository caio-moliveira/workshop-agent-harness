"""Modelo da tabela `harness.runs` — um registro por execução do agente.

Tipos portáveis (Uuid/JSON) para o repo ser testável em SQLite e correto no Postgres
(jsonb via variante). O `schema` é parametrizável: produção usa `harness`; teste usa `None`
(SQLite não tem schemas). A migration 0002 cria a versão Postgres equivalente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# JSON portável: JSONB no Postgres (casa com a migration), JSON genérico no SQLite (teste).
_JSON = sa.JSON().with_variant(JSONB, "postgresql")


def construir_tabela_runs(metadata: sa.MetaData, *, schema: str | None = "harness") -> sa.Table:
    """Define a tabela `runs` no metadata dado (schema parametrizável p/ portabilidade)."""
    return sa.Table(
        "runs",
        metadata,
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pergunta", sa.Text, nullable=False),
        sa.Column("periodo_alvo", sa.Text, nullable=False),
        sa.Column("kpi_alvo", sa.Text, nullable=False),
        sa.Column("dimensao", _JSON, nullable=False),
        sa.Column("sql_executado", _JSON, nullable=False),
        sa.Column("fontes", _JSON, nullable=False),
        sa.Column("relatorio", sa.Text, nullable=False),
        sa.Column("artefatos", _JSON, nullable=False),
        sa.Column("thread_id", sa.Uuid(as_uuid=False), nullable=True),  # agrupa a conversa
        schema=schema,
    )


# Metadata e tabela de produção (schema harness).
METADATA = sa.MetaData()
RUNS = construir_tabela_runs(METADATA, schema="harness")


@dataclass(frozen=True)
class RegistroRun:
    """Os campos de um run a persistir (parte do contrato — `backend.md`)."""

    id: str
    pergunta: str
    periodo_alvo: str
    kpi_alvo: str
    dimensao: dict[str, Any]
    sql_executado: list[str]
    fontes: list[str]
    relatorio: str
    artefatos: dict[str, str]
    thread_id: str | None = None
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def como_linha(self) -> dict[str, Any]:
        """Mapeia o registro para as colunas da tabela `runs`."""
        return {
            "id": self.id,
            "criado_em": self.criado_em,
            "pergunta": self.pergunta,
            "periodo_alvo": self.periodo_alvo,
            "kpi_alvo": self.kpi_alvo,
            "dimensao": self.dimensao,
            "sql_executado": self.sql_executado,
            "fontes": self.fontes,
            "relatorio": self.relatorio,
            "artefatos": self.artefatos,
            "thread_id": self.thread_id,
        }
