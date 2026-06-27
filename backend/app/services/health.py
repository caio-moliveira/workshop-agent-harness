from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import verificar_conexao


@dataclass(frozen=True)
class StatusSaude:
    """Resultado do health check: app no ar + estado do hop ao Postgres."""

    status: str
    banco: str


async def checar_saude(engine: AsyncEngine) -> StatusSaude:
    """Compõe o status de saúde — a lógica vive no service, não no router."""
    banco_ok = await verificar_conexao(engine)
    # `status` acompanha `banco`: nunca reporta "ok" com o banco em erro (a falha real
    # de conexão vira SQLAlchemyError e é tratada como 503 no router).
    return StatusSaude(
        status="ok" if banco_ok else "degraded",
        banco="ok" if banco_ok else "erro",
    )
