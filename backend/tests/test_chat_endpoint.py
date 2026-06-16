"""Teste do contrato HTTP do POST /chat (issue #19) — grafo e harness mockados.

Verifica o seam mais alto (httpx) sem DB nem LLM: o grafo e a persistencia no
harness sao substituidos, isolando o contrato da rota.
"""

from typing import Any

from httpx import ASGITransport, AsyncClient

import app.routers.chat as chatmod
from app.main import app


async def test_post_chat_retorna_relatorio_e_sql(monkeypatch: Any) -> None:
    async def fake_run_chat(pergunta: str, callbacks: Any = None) -> dict[str, Any]:
        return {
            "periodo": "2026-05",
            "relatorio": "Relatorio de teste.",
            "achados": [{"kpi": "faturamento", "dimensao": "regiao=Sul"}],
            "sql_log": ["SELECT 1"],
        }

    async def fake_criar_run(pergunta: str, sessao_id: Any = None) -> str:
        return "run-123"

    async def fake_noop(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(chatmod, "run_chat", fake_run_chat)
    monkeypatch.setattr(chatmod, "get_langfuse_callbacks", lambda run_id=None: [])
    monkeypatch.setattr(chatmod.repo, "criar_run", fake_criar_run)
    monkeypatch.setattr(chatmod.repo, "registrar_tool_call", fake_noop)
    monkeypatch.setattr(chatmod.repo, "finalizar_run", fake_noop)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/chat", json={"pergunta": "como melhorar vendas?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == "run-123"
    assert body["relatorio"] == "Relatorio de teste."
    assert body["sql_executado"] == ["SELECT 1"]
    assert body["achados"][0]["kpi"] == "faturamento"
