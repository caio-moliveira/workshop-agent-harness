"""Porta de entrada conversacional (issue #24): condense-question + roteador.

Reescreve a pergunta de acompanhamento numa pergunta autonoma usando o historico do
turno anterior e classifica a intencao (central / secundario / clarificacao). O
sub-grafo analitico permanece stateless: ele recebe so a pergunta ja reescrita. O
estado de sessao (turnos) vive no schema `harness`.

Sem historico (primeiro turno), nao chama o LLM — intencao=central e a pergunta segue
como esta (deterministico e barato).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage

INTENCOES = ("central", "secundario", "clarificacao")

_PROMPT_ROTEAR = (
    "Voce e a porta de entrada de um agente analitico de vendas. Dado o historico da "
    "conversa e a nova mensagem do gestor, devolva SOMENTE um JSON "
    '{{"intencao": "central"|"secundario"|"clarificacao", "pergunta_reescrita": "..."}}.\n'
    '- "central": pergunta analitica nova, independente do historico. Reescreva como '
    "pergunta autonoma (pode ser quase igual a original).\n"
    '- "secundario": acompanhamento que refina o turno anterior (ex.: "e no Sudeste?", '
    '"e o ticket medio?"). Reescreva incorporando o contexto anterior numa pergunta '
    "autonoma e completa.\n"
    '- "clarificacao": a mensagem e vaga demais para analisar mesmo com o historico. Em '
    '"pergunta_reescrita", coloque a pergunta de volta ao gestor.\n\n'
    "Historico (mais recente primeiro):\n{historico}\n\nNova mensagem: {pergunta}"
)


@dataclass
class Roteamento:
    intencao: str
    pergunta_reescrita: str


def _text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


def _formata_historico(historico: list[dict[str, Any]]) -> str:
    linhas = []
    for turno in historico:
        pergunta = turno.get("pergunta_reescrita") or turno.get("pergunta") or ""
        linhas.append(f"- Gestor perguntou: {pergunta}")
    return "\n".join(linhas)


def _parse(texto: str, pergunta: str) -> Roteamento:
    try:
        inicio, fim = texto.index("{"), texto.rindex("}") + 1
        dados = json.loads(texto[inicio:fim])
        intencao = dados.get("intencao")
        reescrita = (dados.get("pergunta_reescrita") or "").strip()
        if intencao in INTENCOES and reescrita:
            return Roteamento(intencao, reescrita)
    except (ValueError, json.JSONDecodeError):
        pass
    # Fallback seguro: trata como pergunta central, sem reescrita.
    return Roteamento("central", pergunta)


async def rotear(pergunta: str, historico: list[dict[str, Any]], llm: Any) -> Roteamento:
    """Condense-question + classificacao de intencao. Primeiro turno nao chama o LLM."""
    if not historico:
        return Roteamento("central", pergunta)
    texto = _text(
        await llm.ainvoke(
            _PROMPT_ROTEAR.format(historico=_formata_historico(historico), pergunta=pergunta)
        )
    )
    return _parse(texto, pergunta)
