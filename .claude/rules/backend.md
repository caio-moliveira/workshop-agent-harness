---
description: Regras ao editar o backend (FastAPI — camada HTTP e serviços). Aplica a backend/**.
---
# Backend (FastAPI)

- FastAPI **async**; schemas em **Pydantic v2**; lógica de negócio na **service layer**
  (rotas finas, serviços transacionais). Siga a skill `fastapi-patterns`.
- Toda nova **tool do agente** segue o contrato base em `backend/app/agent/tools/base.py`
  (ver `agente.md`).
- **SQL passa pelo guardrail** antes de executar: usuário read-only, allowlist de tabelas,
  `LIMIT` forçado, timeout. Nunca execute SQL cru no schema de negócio sem o guardrail.
- Dados pessoais **nunca** em parâmetros de URL / query string (RNF-03).
- Não edite `infra/**`, `docker-compose.yml` nem `infra/db/migrations/**` sem revisão humana.
- Cada rota/serviço novo nasce com teste (httpx + pytest) cobrindo caminho feliz + um erro.
