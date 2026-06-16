"""Teste do contrato HTTP do POST /chat (issues #19, #23, #24) — streaming SSE.

Verifica o seam mais alto (httpx) sem DB, LLM, Qdrant nem MinIO reais: a porta
conversacional, o stream do grafo, a persistencia no harness e o MinIO sao
substituidos, isolando o contrato da rota. Cobre o streaming (eventos
inicio/progresso/final), a sessao e que a persistencia de artefatos e chamada com
relatorio + grafico (objeto gravado no MinIO).
"""

import json
from typing import Any

from httpx import ASGITransport, AsyncClient

import app.services.chat_service as svc
from app.main import app


async def test_post_chat_stream_e_persiste_artefatos(monkeypatch: Any) -> None:
    estado_final = {
        "periodo": "2026-07",
        "premissas": ["Periodo-alvo assumido = proximo mes (2026-07)."],
        "relatorio": "Relatorio de teste.",
        "achados": [
            {
                "kpi": "faturamento",
                "dimensao": "regiao=Sul",
                "tendencia_gap_pct": -5.0,
                "sazonal_gap_pct": -3.0,
            }
        ],
        "fontes": [{"colecao": "prescricao", "fonte": "minio://presc/frete.md"}],
        "recomendacoes": [{"kpi": "faturamento", "fonte": "minio://presc/frete.md"}],
        "sql_log": ["SELECT 1"],
    }

    async def fake_stream(
        pergunta: str, callbacks: Any = None, fontes_excluidas: Any = None
    ):
        yield "progresso", "planejar"
        yield "progresso", "perna_quantitativa"
        yield "final", estado_final

    async def fake_criar_sessao(rotulo: Any = None) -> str:
        return "sess-1"

    async def fake_criar_run(
        pergunta: str, sessao_id: Any = None, pergunta_reescrita: Any = None
    ) -> str:
        return "run-123"

    async def fake_noop(*args: Any, **kwargs: Any) -> None:
        return None

    capturado: dict[str, Any] = {}

    async def fake_persistir(run_id: str, relatorio: str, grafico: Any) -> dict[str, str]:
        capturado["run_id"] = run_id
        capturado["relatorio"] = relatorio
        capturado["grafico"] = grafico
        chaves = {"relatorio": f"relatorios/{run_id}/relatorio.md"}
        if grafico is not None:
            chaves["grafico"] = f"relatorios/{run_id}/grafico.json"
        return chaves

    monkeypatch.setattr(svc, "run_chat_stream", fake_stream)
    monkeypatch.setattr(svc, "get_langfuse_callbacks", lambda run_id=None: [])
    # historico vazio (turno 1) -> rotear nao chama o LLM; o modelo nem e usado.
    monkeypatch.setattr(svc, "get_chat_model", lambda tier="rapido": None)
    monkeypatch.setattr(svc.repo, "criar_sessao", fake_criar_sessao)
    monkeypatch.setattr(svc.repo, "criar_run", fake_criar_run)
    monkeypatch.setattr(svc.repo, "registrar_tool_call", fake_noop)
    monkeypatch.setattr(svc.repo, "registrar_fonte", fake_noop)
    monkeypatch.setattr(svc.repo, "registrar_trace", fake_noop)
    monkeypatch.setattr(svc.repo, "finalizar_run", fake_noop)
    monkeypatch.setattr(svc.storage, "persistir_artefatos", fake_persistir)

    eventos: list[str] = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", "/chat", json={"pergunta": "como melhorar vendas?"}) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            assert resp.headers["x-run-id"] == "run-123"
            assert resp.headers["x-sessao-id"] == "sess-1"
            async for linha in resp.aiter_lines():
                eventos.append(linha)

    texto = "\n".join(eventos)
    assert "event: inicio" in texto
    assert "event: progresso" in texto
    assert "event: final" in texto

    final_payload = None
    for i, linha in enumerate(eventos):
        if linha == "event: final":
            final_payload = json.loads(eventos[i + 1].removeprefix("data: "))
            break
    assert final_payload is not None
    assert final_payload["run_id"] == "run-123"
    assert final_payload["sessao_id"] == "sess-1"
    assert final_payload["intencao"] == "central"
    assert final_payload["relatorio"] == "Relatorio de teste."
    assert final_payload["sql_executado"] == ["SELECT 1"]
    # Fontes citadas voltam estruturadas e inspecionaveis pelo cliente.
    assert final_payload["fontes"][0]["fonte"] == "minio://presc/frete.md"
    # Artefatos persistidos no MinIO (chaves bucket/objeto).
    assert final_payload["artefatos"]["relatorio"] == "relatorios/run-123/relatorio.md"
    assert final_payload["artefatos"]["grafico"] == "relatorios/run-123/grafico.json"

    # Persistencia foi chamada com o relatorio e um grafico (achados tinham gap).
    assert capturado["relatorio"] == "Relatorio de teste."
    assert capturado["grafico"] is not None
    assert capturado["grafico"]["mark"] == "bar"
