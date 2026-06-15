# Bússola — guia do agente

> Responde: "o que vale para o projeto inteiro?" — lido toda sessão.
> Agente Analítico de Vendas: text-to-SQL (Postgres) + recuperação qualitativa (Qdrant)
> que gera relatórios de melhoria fundamentados. PRD: `ideia.md` · Decisões: `DECISOES.md`.

## Stack
Python 3.13 (uv) · FastAPI · LangGraph (grafo determinístico) · Postgres · Qdrant · MinIO ·
React · nginx · Docker Compose · Langfuse (observabilidade).

## Comandos
- rodar: `docker compose up -d`
- testar: `uv run pytest -q`
- validar (gate rápido): `uv run python scripts/gate.py` (ruff + mypy + pytest)
- avaliar (EDD, sob comando): `/run-evals` → `uv run python evals/run_evals.py`

## Invariantes (nunca quebrar)
1. O agente vive **só no runtime**; nunca participa da ingestão (offline, determinística, sem LLM raciocinando).
2. SQL no schema de negócio é **somente leitura**: usuário read-only + allowlist + `LIMIT` forçado + timeout (guardrail *hard*). Query-checker LLM é *soft*, adicional — nunca substituto.
3. O agente **nunca escreve no schema de negócio**. Só o schema de harness é leitura/escrita.
4. Toda recomendação **cita a fonte**; prescrição sem suporte = falha (grounding).
5. Enriquecimento é **sempre filtrado** (dimensão + tempo + `kpi_alvo`); o filtro **nunca** usa `data_ingestao`.
6. Grafo **determinístico**; o LLM decide só dentro de nós; exatamente 2 tools: `run_sql`, `search(collection,…)`. Sem ReAct livre.

## Onde fica o quê
- regras por área: `.claude/rules/` (backend, agente, ingestao, evals)
- decisões e porquês: `DECISOES.md` (log D1–D11) + `docs/adr/` (os porquês contestáveis)
- avaliação: `evals/` · specs (SDD): `specs/features/`
- continuidade de sessão longa: `HANDOFF.md`

## Ciclo do erro
Toda falha real vira sinal permanente: um teste, um caso de eval, uma regra em `rules/`, ou um
ajuste no gate (`scripts/gate.py`). Não repita um "run ruim" — aperte o harness um dente.
