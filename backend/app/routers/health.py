from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.dependencies import get_engine
from app.services.health import StatusSaude, checar_saude

router = APIRouter(tags=["saude"])


@router.get("/health")
async def health(
    response: Response,
    engine: AsyncEngine = Depends(get_engine),
) -> StatusSaude:
    """Liveness/readiness: confirma a app no ar e o hop até o Postgres."""
    try:
        return await checar_saude(engine)
    except SQLAlchemyError:
        # Banco indisponível: a app responde, mas não está pronta — 503.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StatusSaude(status="degraded", banco="erro")
