# Agente Analítico de Vendas · guia do agente

> Responde: "o que vale para o projeto inteiro?" — carregado em toda sessão. Índice de fatos
> duráveis, não documentação. Regras por área ficam em `.claude/rules/`.

## Stack
Backend **FastAPI** (Python 3.13, `uv`) + **LangChain/LangGraph** (grafo determinístico, sem ReAct
livre). Frontend **React + Vite**. Stores: **Postgres** (schemas `negocio` + `harness`), **Qdrant**
(3 coleções já populadas), **MinIO** (relatórios/gráficos). **nginx** = única porta exposta ao host.
Embeddings OpenAI `text-embedding-3-large` (3072d), só para embeddar a *query* em runtime.
**Langfuse** para observabilidade — *planejado, ainda não no `docker-compose.yml`*.

## Comandos
- subir tudo: `docker compose up -d`
- testar: `uv run pytest -q`
- validar (gate rápido): `uv run ruff check --fix backend && uv run mypy backend && uv run pytest -q` — ou `/validar`
- revisar (antes do commit/PR): subagente `revisor-codigo` — revisão *soft* contra as rules
- medir entrega (time/stakeholders): `/scorecard` — execução medida contra a Definição de Pronto

## Invariantes (nunca quebrar)
- Toda query ao schema **`negocio` é SOMENTE LEITURA** (role RO + allowlist + `LIMIT` + timeout).
  Nunca `INSERT/UPDATE/DELETE/DDL`.
- **App é runtime puro**: nenhuma ingestão/carga no `backend/`. A ingestão vive só em `seed/` (já
  executada) — não a reproduza nem a chame em runtime.
- Enriquecimento Qdrant **sempre filtrado** por `periodo_referencia` + dimensão + `kpi_alvo`.
  **Nunca** filtre por `data_ingestao` (`periodo_referencia ≠ data_ingestao`).
- Toda recomendação prescritiva **amarrada a uma fonte** recuperada. Prescrição sem fonte = falha.
- Grafo LangGraph **determinístico**: o LLM decide só dentro de nós. `search` é tool única
  parametrizada pela coleção, escolhida pelo nó (não por laço do LLM).
- **Stores pré-populados são sagrados**: nunca `docker compose down -v` nem remover volumes
  (apaga ~5 anos de dados + os índices do Qdrant).
- Cada run gravado no schema `harness` (+ Langfuse quando provisionado).

## Onde fica o quê
- regras por área (path-scoped via `paths:`, carregam só ao tocar a área): `.claude/rules/`
- subagente de revisão (verificação *soft*): `.claude/agents/revisor-codigo.md`
- comandos: `.claude/commands/` (`/validar`, `/scorecard`)
- hooks (estilo automático no `PostToolUse` + gate de validação no `Stop`) e permissões: `.claude/settings.json`
- MCP (infra somente-leitura, inspecionável): `.mcp.json` na raiz — Postgres RO p/ o agente ler o schema `negocio`
- Definição de Pronto (contrato mensurável de "entregue"): `.claude/rules/definicao-de-pronto.md`
- métricas de entrega: `metrics/` — `entregas.jsonl` (1 linha/issue) + `README.md` (schema)
- decisões e porquês: `docs/adr/`
- golden dataset: `seed/evals/golden/` · narrativas plantadas: `seed/NARRATIVAS.md`
- DDL de referência: `seed/schema.sql` · ingestão (offline, já feita): `seed/`
- handoff de sessão: `HANDOFF.md`

## Layout do backend (convenção)
`backend/app/` (FastAPI: routers finos + `services/`) · `backend/agent/` (grafo, nós, tools
`run_sql`/`search`, state) · `backend/harness/` (persistência de runs/traces) · `backend/tests/`.
Infra: `infra/nginx/`.

## Agent skills

### Issue tracker

Issues e PRDs vivem como GitHub Issues do repo `caio-moliveira/workshop-agent-harness`, via `gh`
CLI. Ver `docs/agents/issue-tracker.md`.

### Triage labels

Cinco labels canônicas com nomes-padrão (`needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`). Ver `docs/agents/triage-labels.md`.

### Domain docs

Single-context: um `CONTEXT.md` + `docs/adr/` na raiz. Ver `docs/agents/domain.md`.
