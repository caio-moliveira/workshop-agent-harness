"""Embedder da *query* (OpenAI) — só vetoriza a pergunta em runtime, sem LLM raciocinando.

A `search` recebe um `Embedder` injetado (callable async), o que mantém a tool testável
offline: em teste passa-se um fake; em produção, `criar_embedder` embrulha o SDK da OpenAI.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from openai import OpenAI

# Contrato mínimo que a `search` exige: texto -> vetor.
Embedder = Callable[[str], Awaitable[list[float]]]


def criar_embedder(client: OpenAI, *, model: str, dim: int) -> Embedder:
    """Embrulha o SDK da OpenAI num `Embedder`. O `to_thread` evita bloquear o event loop."""

    async def _embed(texto: str) -> list[float]:
        resp = await asyncio.to_thread(
            lambda: client.embeddings.create(model=model, input=[texto], dimensions=dim)
        )
        return list(resp.data[0].embedding)

    return _embed
