"""Testes da porta conversacional: condense-question + roteador (issue #24).

Sem rede: o LLM e um FakeListChatModel. Cobre o atalho do primeiro turno (sem
historico, sem LLM), a reescrita contextual de acompanhamento e a classificacao de
intencao (central / secundario / clarificacao), alem do fallback de parse.
"""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from agent.conversa import Roteamento, rotear


async def test_primeiro_turno_e_central_sem_chamar_llm() -> None:
    # Sem historico, nem deve tocar no LLM (passamos um modelo que explodiria se usado).
    class LlmProibido:
        async def ainvoke(self, *a: object, **k: object) -> object:
            raise AssertionError("LLM nao deve ser chamado no primeiro turno")

    r = await rotear("como vao as vendas?", [], LlmProibido())
    assert r == Roteamento("central", "como vao as vendas?")


async def test_acompanhamento_reescreve_com_contexto() -> None:
    historico = [{"pergunta_reescrita": "como melhorar o faturamento por regiao no proximo mes?"}]
    llm = FakeListChatModel(
        responses=[
            '{"intencao": "secundario", "pergunta_reescrita": '
            '"como melhorar o faturamento na regiao Sudeste no proximo mes?"}'
        ]
    )
    r = await rotear("e no Sudeste?", historico, llm)
    assert r.intencao == "secundario"
    assert "Sudeste" in r.pergunta_reescrita


async def test_clarificacao_quando_vago() -> None:
    historico = [{"pergunta": "como vao as vendas?"}]
    llm = FakeListChatModel(
        responses=['{"intencao": "clarificacao", "pergunta_reescrita": "Pode detalhar o que deseja?"}']
    )
    r = await rotear("e o resto?", historico, llm)
    assert r.intencao == "clarificacao"
    assert r.pergunta_reescrita


async def test_parse_invalido_cai_em_central(monkeypatch: pytest.MonkeyPatch) -> None:
    historico = [{"pergunta": "x"}]
    llm = FakeListChatModel(responses=["resposta sem json"])
    r = await rotear("pergunta original", historico, llm)
    assert r == Roteamento("central", "pergunta original")
