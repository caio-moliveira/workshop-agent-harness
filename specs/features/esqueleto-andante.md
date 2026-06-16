# Spec — Esqueleto andante (docker compose + `POST /chat` stub)

> Issue **#1** · fatia vertical *tracer-bullet*. Prova a cadeia HTTP ponta-a-ponta e a
> reprodutibilidade do ambiente (RNF-05). **Sem agente real — só o trilho.**

## Objetivo

A menor fatia que atravessa toda a cadeia de serving: `docker compose up` sobe **nginx →
FastAPI → Postgres (vazio)**, e `POST /chat` recebe uma pergunta em linguagem natural e devolve
uma **resposta-stub**. Estabelece a estrutura do backend (camada HTTP, Pydantic v2, service layer
fina) e o trilho onde as próximas issues plugam o agente.

## Escopo

**Dentro:**
- `docker-compose.yml` com 3 serviços: `nginx` (reverse proxy), `api` (FastAPI/uvicorn), `postgres` (vazio).
- App FastAPI async: `GET /health` e `POST /chat` (stub). Schemas Pydantic v2; lógica numa service layer fina.
- nginx encaminhando o tráfego externo para o `api`.
- Smoke test (httpx + pytest): caminho feliz do `/chat` + um erro (validação).
- `pyproject.toml` com as deps (fastapi, uvicorn, pydantic; dev: httpx, pytest, ruff, mypy).

**Fora (entra em issues posteriores):**
- Agente, LangGraph, `run_sql`, `search` — nenhuma lógica analítica real.
- Qdrant, MinIO, Langfuse.
- Schemas `negocio`/`harness` e o papel `agente_ro` (Postgres sobe **vazio**; schemas vêm na #2/#4).
- Streaming, sessão multi-turno, persistência de relatório.

## Contrato `POST /chat`

Request (Pydantic v2):
```json
{ "pergunta": "como melhorar minhas vendas no próximo mês?" }
```
- `pergunta: str` — obrigatória, `min_length=1`.

Response `200`:
```json
{ "resposta": "[stub] recebi: 'como melhorar minhas vendas no próximo mês?'. Agente ainda não implementado.", "stub": true }
```

`GET /health` → `200 { "status": "ok" }` (usado pelo healthcheck do compose e pra provar o hop via nginx).

## Cenários (BDD)

```gherkin
Funcionalidade: Trilho HTTP do chat (esqueleto andante)

  Cenário: Ambiente sobe reprodutível
    Dado um checkout limpo com .env configurado
    Quando eu rodo "docker compose up -d"
    Então os serviços nginx, api e postgres ficam de pé sem erro
    E "GET /health" através do nginx responde 200

  Cenário: Caminho feliz do /chat
    Dado o serviço no ar
    Quando eu envio POST /chat com {"pergunta": "como melhorar minhas vendas?"}
    Então recebo 200
    E o corpo tem "stub": true e ecoa a pergunta recebida

  Cenário: Requisição inválida (sem pergunta)
    Dado o serviço no ar
    Quando eu envio POST /chat com corpo {} ou pergunta vazia
    Então recebo 422 (erro de validação) e nenhum stub é gerado

  Cenário: A requisição atravessa o nginx até o FastAPI
    Dado o ambiente subido via compose
    Quando eu envio POST /chat para a porta exposta do nginx
    Então a resposta-stub do FastAPI retorna pela mesma cadeia
```

## Seam de teste

Seam mais alto (PRD §Testing): **HTTP via httpx**. O smoke test exercita o app FastAPI
(`ASGITransport`/`TestClient`) cobrindo feliz + erro de validação — roda no gate (pytest).
O hop pelo nginx é verificado com o stack de pé (`docker compose up`), fora do gate unitário.

## Critérios de aceite (espelham a issue #1)

- [ ] `docker compose up` sobe FastAPI, Postgres e nginx sem erro
- [ ] `POST /chat` responde 200 com corpo stub a partir da pergunta enviada
- [ ] A requisição passa pelo nginx até o FastAPI
- [ ] Smoke test (httpx + pytest) cobre o caminho feliz do `/chat` + um erro
- [ ] `uv run python scripts/gate.py` verde

## Decisões de implementação

- **Postgres sobe mas o app não depende dele ainda** (sem conexão/migration nesta fatia) — só prova
  que sobe no compose. Conexão entra quando houver o que ler/gravar (#2/#4).
- **Só o nginx é exposto ao host** (porta 8080→80); `api` fica interno (8000), forçando o hop pelo proxy.
- Estrutura `backend/app/{api,schemas,services,core}` conforme a skill `fastapi-templates` e `rules/backend.md`.
```
