from __future__ import annotations

from typing import Any

from evals.judge import JuizOpenAI


class _FakeResp:
    def __init__(self, conteudo: str) -> None:
        self.choices = [type("C", (), {"message": type("M", (), {"content": conteudo})()})()]


class _FakeCompletions:
    def __init__(self, conteudo: str) -> None:
        self._conteudo = conteudo
        self.prompt_recebido: str | None = None

    def create(self, **kwargs: Any) -> _FakeResp:
        self.prompt_recebido = kwargs["messages"][0]["content"]
        return _FakeResp(self._conteudo)


class _FakeClient:
    def __init__(self, conteudo: str) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions(conteudo)})()


async def test_juiz_formata_prompt_sem_quebrar_e_parseia_score() -> None:
    """Regressão: o JSON de exemplo no prompt tem chaves literais — não pode quebrar o .format()."""
    client = _FakeClient('{"score": 0.8, "justificativa": "alinhado"}')
    juiz = JuizOpenAI(client, modelo="gpt-4o")  # type: ignore[arg-type]
    v = await juiz.avaliar(recomendacao_esperada="ref {com chave}", relatorio="rel")
    assert v.score == 0.8
    assert v.justificativa == "alinhado"
    # o prompt incluiu as duas seções (format aplicado corretamente)
    prompt = client.chat.completions.prompt_recebido  # type: ignore[attr-defined]
    assert "RECOMENDAÇÃO DE REFERÊNCIA" in prompt and "ref {com chave}" in prompt


async def test_juiz_clampa_score_e_trata_lixo() -> None:
    """Score fora de [0,1] é clampado; resposta ilegível vira 0.0."""
    j_alto = JuizOpenAI(_FakeClient('{"score": 5, "justificativa": "x"}'), modelo="m")  # type: ignore[arg-type]
    assert (await j_alto.avaliar(recomendacao_esperada="r", relatorio="x")).score == 1.0

    j_lixo = JuizOpenAI(_FakeClient("não é json"), modelo="m")  # type: ignore[arg-type]
    assert (await j_lixo.avaliar(recomendacao_esperada="r", relatorio="x")).score == 0.0
