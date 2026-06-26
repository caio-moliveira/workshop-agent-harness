"""LLM-as-judge: pontua faithfulness e answer-relevancy da recomendação do agente.

Injetável (Protocol `Juiz`) para o runner testar offline com um fake; a impl OpenAI usa o
SDK com saída JSON e temperatura 0 (determinismo possível).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI


@dataclass(frozen=True)
class NotaJuiz:
    """Notas 0..1 do juiz para uma recomendação."""

    faithfulness: float  # fiel ao esperado, sem contradizer/alucinar
    answer_relevancy: float  # responde à pergunta do gestor
    justificativa: str = ""


class Juiz(Protocol):
    """Contrato do juiz (permite fake em teste)."""

    async def avaliar(
        self, *, pergunta: str, recomendacao_obtida: str, recomendacao_esperada: str
    ) -> NotaJuiz: ...


_PROMPT = (
    "Você é um avaliador rigoroso. Dada a PERGUNTA do gestor, a recomendação ESPERADA "
    "(gabarito) e a recomendação OBTIDA do agente, pontue de 0 a 1:\n"
    "- faithfulness: a OBTIDA é consistente com a ESPERADA, sem contradizê-la nem inventar?\n"
    "- answer_relevancy: a OBTIDA responde diretamente à PERGUNTA?\n"
    'Responda SOMENTE JSON: {{"faithfulness": <0..1>, "answer_relevancy": <0..1>, '
    '"justificativa": "<1 frase>"}}\n\n'
    "PERGUNTA: {pergunta}\nESPERADA: {esperada}\nOBTIDA: {obtida}"
)


class JuizOpenAI:
    """Juiz baseado no SDK OpenAI (model id vem de fora — não hardcoded)."""

    def __init__(self, client: OpenAI, *, modelo: str) -> None:
        self._client = client
        self._modelo = modelo

    async def avaliar(
        self, *, pergunta: str, recomendacao_obtida: str, recomendacao_esperada: str
    ) -> NotaJuiz:
        prompt = _PROMPT.format(
            pergunta=pergunta, esperada=recomendacao_esperada, obtida=recomendacao_obtida
        )

        def _chamar() -> str:
            resp = self._client.chat.completions.create(
                model=self._modelo,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or "{}"

        bruto: dict[str, Any] = json.loads(await asyncio.to_thread(_chamar))
        return NotaJuiz(
            faithfulness=float(bruto.get("faithfulness", 0.0)),
            answer_relevancy=float(bruto.get("answer_relevancy", 0.0)),
            justificativa=str(bruto.get("justificativa", "")),
        )
