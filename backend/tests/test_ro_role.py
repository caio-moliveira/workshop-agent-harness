"""Prova as permissoes do role read-only do agente (issue #16).

Teste de integracao contra o Postgres real (a migration 0001 precisa estar
aplicada). Faz skip gracioso quando o banco nao esta acessivel, para o gate
seguir verde sem a stack de pe.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def test_agente_ro_le_negocio_mas_nao_escreve() -> None:
    if not settings.agente_ro_password:
        pytest.skip("AGENTE_RO_PASSWORD nao definida")

    # Confere via conexao admin que a stack esta de pe e a migration foi aplicada.
    admin = create_async_engine(settings.database_url)
    try:
        async with admin.connect() as conn:
            tem_harness = (
                await conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.schemata "
                        "WHERE schema_name = 'harness'"
                    )
                )
            ).first()
    except Exception:
        pytest.skip("Postgres indisponivel para teste de integracao")
    finally:
        await admin.dispose()

    if tem_harness is None:
        pytest.skip("migration 0001 nao aplicada (schema harness ausente)")

    ro = create_async_engine(settings.agente_ro_url)
    try:
        # SELECT em negocio funciona.
        async with ro.connect() as conn:
            total = (
                await conn.execute(text("SELECT count(*) FROM negocio.regioes"))
            ).scalar_one()
        assert total >= 0

        # INSERT em negocio e negado (somente leitura).
        with pytest.raises(DBAPIError):
            async with ro.begin() as conn:
                await conn.execute(
                    text("INSERT INTO negocio.regioes (id, nome) VALUES (999, 'proibido')")
                )

        # DDL e negado.
        with pytest.raises(DBAPIError):
            async with ro.begin() as conn:
                await conn.execute(text("CREATE TABLE negocio.t_proibida (id integer)"))
    finally:
        await ro.dispose()
