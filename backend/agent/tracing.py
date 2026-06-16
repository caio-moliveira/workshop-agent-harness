"""Tracing via Langfuse (cloud) — best-effort (issue #19).

Se as chaves nao estiverem no ambiente, retorna lista vazia de callbacks: o fluxo
roda sem tracing e nunca quebra (RNF do PRD). Langfuse le as chaves do ambiente.
"""

from __future__ import annotations

from typing import Any

from app.config import settings


def get_langfuse_callbacks(run_id: str | None = None) -> list[Any]:
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler()]
    except Exception:
        # Ausencia/erro de Langfuse nunca derruba o /chat.
        return []
