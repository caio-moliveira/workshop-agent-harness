"""Fabrica de modelos de chat (Claude via LangChain, provider-agnostic).

Dois tiers (PRD): `forte` (planejamento/sintese) e `rapido` (SQL/roteamento).
Opus 4.8 nao aceita `temperature`/`top_p` — por isso nao os passamos.
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_chat_model(tier: str = "forte") -> BaseChatModel:
    model = settings.llm_model_forte if tier == "forte" else settings.llm_model_rapido
    return init_chat_model(
        model,
        model_provider="anthropic",
        api_key=settings.anthropic_api_key or None,
        max_tokens=4096,
    )
