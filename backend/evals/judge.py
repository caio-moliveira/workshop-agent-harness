"""Faithfulness via LLM-judge — avalia se o relatório do agente é FIEL aos dados e
alinhado ao desfecho esperado (sem contradição, com fonte). É I/O (chama o LLM), então
fica isolado da pontuação pura; em teste, usa-se um fake que implementa `Juiz`.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI


@dataclass(frozen=True)
class VeredictoJuiz:
    """Resultado do judge: score 0..1 + justificativa (entra no trace inspecionável)."""

    score: float
    justificativa: str


class Juiz(Protocol):
    """Contrato do avaliador de faithfulness (permite fake em teste)."""

    async def avaliar(self, *, recomendacao_esperada: str, relatorio: str) -> VeredictoJuiz: ...


_PROMPT_JUIZ = (
    "Você é um avaliador rigoroso. Compare o RELATÓRIO de um agente analítico com a "
    "RECOMENDAÇÃO DE REFERÊNCIA (o desfecho correto, escrito por um especialista).\n"
    "Dê uma nota de FAITHFULNESS de 0 a 1 medindo se o relatório:\n"
    "- captura o diagnóstico central da referência (causa do problema),\n"
    "- aponta a ação certa e evita a ação errada quando a referência as distingue,\n"
    "- não contradiz nem inventa fatos fora da referência.\n"
    "Não exija texto idêntico — avalie o conteúdo. Responda SOMENTE um JSON "
    '{{"score": <0..1>, "justificativa": "<1-2 frases>"}}.\n\n'
    "RECOMENDAÇÃO DE REFERÊNCIA:\n{esperada}\n\nRELATÓRIO DO AGENTE:\n{relatorio}"
)


class JuizOpenAI:
    """Implementação OpenAI do judge (temperatura 0 para estabilidade do score)."""

    def __init__(self, client: OpenAI, *, modelo: str) -> None:
        self._client = client
        self._modelo = modelo

    async def avaliar(self, *, recomendacao_esperada: str, relatorio: str) -> VeredictoJuiz:
        prompt = _PROMPT_JUIZ.format(esperada=recomendacao_esperada, relatorio=relatorio)

        def _chamar() -> str:
            resp = self._client.chat.completions.create(
                model=self._modelo,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or "{}"

        bruto = await asyncio.to_thread(_chamar)
        try:
            obj = json.loads(bruto)
            score = max(0.0, min(1.0, float(obj.get("score", 0.0))))
            return VeredictoJuiz(score=score, justificativa=str(obj.get("justificativa", "")))
        except (json.JSONDecodeError, ValueError, TypeError):
            return VeredictoJuiz(score=0.0, justificativa="resposta do juiz ilegível")
