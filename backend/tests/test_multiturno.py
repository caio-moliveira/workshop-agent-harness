"""Dialogo multi-turno ponta a ponta no seam HTTP (issue #24).

Repo do harness em memoria (sessao + turnos + fontes acumuladas), grafo e MinIO
mockados. Prova: turno 2 usa o contexto do turno 1 (reescrita contextual via roteador),
e as prescricoes ja recomendadas no turno 1 entram como `fontes_excluidas` no turno 2
(recomendacao nao se repete).
"""

import json
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

import app.services.chat_service as svc
from app.main import app

FONTE_X = "minio://presc/2024-08-sul-frete-gratis.md"


class FakeHarness:
    """Estado de sessao/turnos/fontes em memoria, espelhando o repo real."""

    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}
        self.run_to_sessao: dict[str, str] = {}
        self.fontes_por_sessao: dict[str, list[str]] = {}
        self._seq = 0

    async def criar_sessao(self, rotulo: Any = None) -> str:
        return "sess-A"

    async def criar_run(
        self, pergunta: str, sessao_id: Any = None, pergunta_reescrita: Any = None
    ) -> str:
        self._seq += 1
        run_id = f"run-{self._seq}"
        self.runs[run_id] = {
            "pergunta": pergunta,
            "pergunta_reescrita": pergunta_reescrita,
            "relatorio": None,
            "status": "em_andamento",
            "sessao_id": sessao_id,
        }
        self.run_to_sessao[run_id] = sessao_id or ""
        return run_id

    async def historico_sessao(self, sessao_id: str, limite: int = 5) -> list[dict[str, Any]]:
        return [
            {
                "pergunta": r["pergunta"],
                "pergunta_reescrita": r["pergunta_reescrita"],
                "relatorio": r["relatorio"],
            }
            for r in self.runs.values()
            if r["sessao_id"] == sessao_id and r["status"] == "concluido"
        ]

    async def fontes_prescricao_da_sessao(self, sessao_id: str) -> list[str]:
        return list(self.fontes_por_sessao.get(sessao_id, []))

    async def registrar_tool_call(self, *a: Any, **k: Any) -> None:
        return None

    async def registrar_fonte(
        self, run_id: str, colecao: str, fonte: Any = None, payload: Any = None, score: Any = None
    ) -> None:
        if colecao == "prescricao" and fonte:
            sessao = self.run_to_sessao.get(run_id, "")
            self.fontes_por_sessao.setdefault(sessao, []).append(fonte)

    async def registrar_trace(self, run_id: str, evento: str, dados: Any = None) -> None:
        return None

    async def finalizar_run(self, run_id: str, relatorio: str, status: str = "concluido") -> None:
        self.runs[run_id]["relatorio"] = relatorio
        self.runs[run_id]["status"] = status


def _eventos(linhas: list[str]) -> dict[str, dict[str, Any]]:
    """Coleta o ultimo payload de cada tipo de evento SSE."""
    out: dict[str, dict[str, Any]] = {}
    for i, linha in enumerate(linhas):
        if linha.startswith("event: ") and i + 1 < len(linhas):
            tipo = linha.removeprefix("event: ")
            out[tipo] = json.loads(linhas[i + 1].removeprefix("data: "))
    return out


async def _post(client: AsyncClient, pergunta: str, sessao_id: str | None) -> dict[str, dict[str, Any]]:
    corpo: dict[str, Any] = {"pergunta": pergunta}
    if sessao_id is not None:
        corpo["sessao_id"] = sessao_id
    linhas: list[str] = []
    async with client.stream("POST", "/chat", json=corpo) as resp:
        assert resp.status_code == 200
        async for linha in resp.aiter_lines():
            linhas.append(linha)
    return _eventos(linhas)


async def test_dialogo_dois_turnos_reescreve_e_suprime(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = FakeHarness()
    chamadas: list[dict[str, Any]] = []

    async def fake_stream(pergunta: str, callbacks: Any = None, fontes_excluidas: Any = None):
        chamadas.append({"pergunta": pergunta, "fontes_excluidas": list(fontes_excluidas or [])})
        yield "progresso", "planejar"
        if "Sudeste" in pergunta:
            # Turno 2: a prescricao do Sul ja foi recomendada -> nada de novo.
            yield "final", {
                "periodo": "2026-07",
                "relatorio": "Sem nova prescricao para o Sudeste.",
                "achados": [{"kpi": "faturamento", "dimensao": "regiao=Sudeste"}],
                "fontes": [],
                "recomendacoes": [],
                "sql_log": ["SELECT 2"],
            }
        else:
            # Turno 1: recomenda a fonte X (frete gratis no Sul).
            yield "final", {
                "periodo": "2026-07",
                "relatorio": "Recomendo frete gratis no Sul.",
                "achados": [{"kpi": "faturamento", "dimensao": "regiao=Sul"}],
                "fontes": [{"colecao": "prescricao", "fonte": FONTE_X}],
                "recomendacoes": [{"kpi": "faturamento", "fonte": FONTE_X}],
                "sql_log": ["SELECT 1"],
            }

    # Roteador: turno 2 (com historico) e classificado secundario e reescrito com contexto.
    fake_llm = FakeListChatModel(
        responses=[
            '{"intencao": "secundario", "pergunta_reescrita": '
            '"como melhorar o faturamento na regiao Sudeste no proximo mes?"}'
        ]
    )

    monkeypatch.setattr(svc, "run_chat_stream", fake_stream)
    monkeypatch.setattr(svc, "get_langfuse_callbacks", lambda run_id=None: [])
    monkeypatch.setattr(svc, "get_chat_model", lambda tier="rapido": fake_llm)
    for nome in (
        "criar_sessao",
        "criar_run",
        "historico_sessao",
        "fontes_prescricao_da_sessao",
        "registrar_tool_call",
        "registrar_fonte",
        "registrar_trace",
        "finalizar_run",
    ):
        monkeypatch.setattr(svc.repo, nome, getattr(harness, nome))

    async def fake_persistir(run_id: str, relatorio: str, grafico: Any) -> dict[str, str]:
        return {"relatorio": f"relatorios/{run_id}/relatorio.md"}

    monkeypatch.setattr(svc.storage, "persistir_artefatos", fake_persistir)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Turno 1: pergunta central, sem sessao.
        t1 = await _post(client, "como melhorar o faturamento por regiao?", None)
        sessao_id = t1["inicio"]["sessao_id"]
        assert sessao_id == "sess-A"
        assert t1["final"]["intencao"] == "central"
        # Fonte X foi recomendada e ficou registrada na sessao.
        assert harness.fontes_por_sessao["sess-A"] == [FONTE_X]

        # Turno 2: acompanhamento "e no Sudeste?" reusando a sessao.
        t2 = await _post(client, "e no Sudeste?", sessao_id)

    # Reescrita contextual: o roteador classificou secundario e reescreveu com o contexto.
    assert t2["final"]["intencao"] == "secundario"
    assert "Sudeste" in t2["final"]["pergunta_reescrita"]

    # O grafo do turno 2 recebeu a pergunta reescrita e a fonte X como excluida.
    assert "Sudeste" in chamadas[1]["pergunta"]
    assert chamadas[1]["fontes_excluidas"] == [FONTE_X]
    # Turno 1 nao tinha o que excluir.
    assert chamadas[0]["fontes_excluidas"] == []
