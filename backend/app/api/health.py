"""Healthcheck: prova que o app está de pé e conecta no Postgres (SELECT 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.database import get_connection

router = APIRouter(tags=["infra"])


@router.get("/health")
async def health(conn: AsyncConnection = Depends(get_connection)) -> dict[str, str]:
    await conn.execute(text("SELECT 1"))
    return {"status": "ok"}
