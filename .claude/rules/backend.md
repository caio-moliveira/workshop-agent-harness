---
# Convenções do backend FastAPI — carrega ao tocar a app web (não o grafo do agente).
paths:
  - "backend/app/**"
---

# Backend — FastAPI

A camada web é fina: **roteia, valida, delega.** A lógica vive em `services/` e em `backend/agent/`.

- **Routers finos:** um `router` só extrai/valida entrada (Pydantic), chama um `service` e
  formata a saída. Nada de regra de negócio ou SQL no router.
- **`services/`** orquestra (chama o grafo do agente, persiste artefatos no MinIO, monta o
  payload de streaming). É onde mora a lógica de aplicação.
- **Config só via `app.config.settings`** (pydantic-settings). Nunca leia `os.environ` solto
  nem hardcode URL/senha. No container o compose injeta `DATABASE_URL` apontando p/ `postgres`.
- **Async de ponta a ponta:** handlers `async def`, SQLAlchemy async, sem chamada bloqueante no
  event loop.
- **Streaming:** a resposta do chat é SSE (`text/event-stream`). Emita eventos incrementais; não
  bufferize o relatório inteiro antes de responder.
- **Erros:** traduza falha de domínio em `HTTPException` com status correto; não vaze stack trace
  nem SQL cru para o cliente.
- **Única porta exposta é o nginx** — não publique a porta da API direto no host.
- **Todo run gravado no schema `harness`** (`backend/harness/`). Persistência de run é parte do
  contrato, não opcional.
