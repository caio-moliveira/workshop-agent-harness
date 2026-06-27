"""Interface do LLM dos nós (provider OpenAI) — o LLM decide só DENTRO de um nó.

Três responsabilidades, estruturadas para serem mockáveis e determinísticas em teste:
- `planejar`: extrai `kpi_alvo` + `dimensao` da pergunta (saída validada contra o catálogo).
- `diagnosticar`: redige o diagnóstico a partir dos dados + diagnósticos recuperados.
- `recomendar`: redige UMA recomendação amarrada a UMA fonte de prescrição (grounding).

Model id vem de `settings` (`llm_model_forte`/`llm_model_rapido`) — nunca hardcoded.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

from openai import OpenAI
from pydantic import BaseModel, Field

from agent.catalogo import KPIS, VALORES_DIMENSAO, dimensao_valida


class Plano(BaseModel):
    """O que investigar — escolhido pelo LLM no nó `planejar`, validado contra o catálogo.

    `precisa_clarificar` só é True quando NADA é resolvível (best-effort: na dúvida, o LLM
    assume um default sensato e o declara como premissa, em vez de devolver pergunta).
    """

    kpi_alvo: str
    dimensao: dict[str, str] = Field(default_factory=dict)
    precisa_clarificar: bool = False
    pergunta_clarificacao: str = ""


class PlanoInvalidoError(ValueError):
    """O LLM escolheu um KPI/dimensão fora do catálogo."""


def validar_plano(plano: Plano) -> Plano:
    """Garante que o plano usa vocabulário conhecido — barra alucinação de KPI/dimensão."""
    if plano.precisa_clarificar:
        return plano  # nada a validar — o fluxo vai pedir clarificação, não investigar
    if plano.kpi_alvo not in KPIS:
        raise PlanoInvalidoError(f"KPI fora do catálogo: {plano.kpi_alvo!r}.")
    if not dimensao_valida(plano.dimensao):
        raise PlanoInvalidoError(f"Dimensão inválida: {plano.dimensao!r}.")
    return plano


class ModeloLLM(Protocol):
    """Contrato mínimo que os nós exigem (permite fake em teste, sem chamar OpenAI)."""

    async def condensar(self, pergunta: str, contexto_anterior: str) -> str: ...

    async def planejar(self, pergunta: str) -> Plano: ...

    async def diagnosticar(
        self, *, pergunta: str, periodo_alvo: str, dados: str, diagnosticos: str
    ) -> str: ...

    async def recomendar(self, *, pergunta: str, prescricao: str, dados: str) -> str: ...


_PROMPT_CONDENSAR = (
    "Numa conversa de análise de vendas, o usuário fez um acompanhamento que pode depender "
    "do contexto anterior. Reescreva a NOVA mensagem como uma pergunta AUTÔNOMA e completa, "
    "herdando o que faltar do contexto (KPI, período, dimensão). Se já for autônoma, repita-a "
    "igual. Responda SOMENTE a pergunta reescrita, sem aspas.\n\n"
    "CONTEXTO ANTERIOR: {contexto}\nNOVA MENSAGEM: {pergunta}"
)


_PROMPT_PLANEJAR = (
    "Você roteia perguntas de um gestor comercial para um KPI e uma dimensão. "
    "KPIs válidos: {kpis}. Dimensões e valores válidos: {dims}. "
    "BEST-EFFORT: diante de ambiguidade, ASSUMA um default sensato (ex.: kpi_alvo='faturamento', "
    "dimensao vazia=agregado) — não peça esclarecimento. Só marque precisa_clarificar=true quando "
    "a pergunta for IMPOSSÍVEL de resolver (vazia/sem sentido de negócio). "
    'Responda SOMENTE um JSON {{"kpi_alvo": <kpi>, "dimensao": {{<chave>: <valor>}}, '
    '"precisa_clarificar": <bool>, "pergunta_clarificacao": "<texto se precisa_clarificar>"}}. '
    "Pergunta: {pergunta}"
)


class LLMOpenAI:
    """Implementação OpenAI da interface. Embrulha o SDK; `to_thread` não bloqueia o loop."""

    def __init__(self, client: OpenAI, *, modelo_forte: str, modelo_rapido: str) -> None:
        self._client = client
        self._forte = modelo_forte
        self._rapido = modelo_rapido

    async def _chat(self, modelo: str, prompt: str, *, json_mode: bool = False) -> str:
        kwargs: dict[str, Any] = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await asyncio.to_thread(lambda: self._client.chat.completions.create(**kwargs))
        return resp.choices[0].message.content or ""

    async def condensar(self, pergunta: str, contexto_anterior: str) -> str:
        prompt = _PROMPT_CONDENSAR.format(contexto=contexto_anterior, pergunta=pergunta)
        texto = await self._chat(self._rapido, prompt)
        return texto.strip() or pergunta

    async def planejar(self, pergunta: str) -> Plano:
        prompt = _PROMPT_PLANEJAR.format(
            kpis=", ".join(sorted(KPIS)),
            dims={k: sorted(v) for k, v in VALORES_DIMENSAO.items()},
            pergunta=pergunta,
        )
        bruto = await self._chat(self._rapido, prompt, json_mode=True)
        return validar_plano(Plano.model_validate(json.loads(bruto)))

    async def diagnosticar(
        self, *, pergunta: str, periodo_alvo: str, dados: str, diagnosticos: str
    ) -> str:
        prompt = (
            f"Pergunta: {pergunta}\nPeríodo-alvo: {periodo_alvo}\n"
            f"Dados quantitativos (tendência/sazonal):\n{dados}\n"
            f"Diagnósticos recuperados:\n{diagnosticos}\n\n"
            "Escreva um diagnóstico curto (3-5 frases) explicando se o KPI está fraco, "
            "separando queda real de variação sazonal. NÃO recomende ações aqui."
        )
        return await self._chat(self._forte, prompt)

    async def recomendar(self, *, pergunta: str, prescricao: str, dados: str) -> str:
        prompt = (
            f"Pergunta: {pergunta}\nDados:\n{dados}\n"
            f"Documento de prescrição (fonte rastreável):\n{prescricao}\n\n"
            "Escreva UMA recomendação acionável baseada ESTRITAMENTE neste documento. "
            "Se o documento indica resultado positivo, recomende repetir; se negativo/nulo, "
            "recomende evitar. 1-2 frases. Não invente nada fora do documento."
        )
        return await self._chat(self._forte, prompt)


def criar_llm(client: OpenAI, *, modelo_forte: str, modelo_rapido: str) -> ModeloLLM:
    """Fábrica do LLM de produção (OpenAI)."""
    return LLMOpenAI(client, modelo_forte=modelo_forte, modelo_rapido=modelo_rapido)
