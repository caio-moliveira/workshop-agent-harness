"""Smoke test do POST /chat: caminho feliz (stub) + erro de validação."""

from __future__ import annotations

from httpx import AsyncClient


async def test_chat_caminho_feliz(client: AsyncClient) -> None:
    r = await client.post("/chat", json={"pergunta": "como melhorar minhas vendas?"})
    assert r.status_code == 200
    body = r.json()
    assert body["stub"] is True
    assert "como melhorar minhas vendas?" in body["resposta"]


async def test_chat_sem_pergunta(client: AsyncClient) -> None:
    r = await client.post("/chat", json={})
    assert r.status_code == 422


async def test_chat_pergunta_vazia(client: AsyncClient) -> None:
    r = await client.post("/chat", json={"pergunta": ""})
    assert r.status_code == 422
