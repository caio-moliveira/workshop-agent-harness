"""Agrega os routers da API."""

from __future__ import annotations

from fastapi import APIRouter

from app.api import chat, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
