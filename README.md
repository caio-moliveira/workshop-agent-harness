# Agente Analítico de Vendas — *Bússola*

Assistente agêntico que costura **text-to-SQL** (Postgres, somente leitura) com **recuperação
qualitativa** (Qdrant) para gerar **relatórios de melhoria de vendas fundamentados** — cruzando o
*o quê* (números) com o *porquê* (voz do cliente) e o *o que fazer* (playbooks que já funcionaram).

Projeto de **workshop conduzido como produto de mundo real**. O foco não é só o app: é o **método**
— sair de uma ideia solta e chegar em issues prontas para um agente implementar, tudo conduzido por
um **agent harness baseado em skills**.

> Este README conta **como chegamos até aqui**: o que já estava posto e a cadeia de skills que nos
> levou da *ideia* → *PRD* → *harness* → *issues* → *implementação*.

---

## 1. Antes de tudo — o que já estava posto

Quatro coisas foram preparadas **antes** de a cadeia de skills começar:

| O quê | Onde | Estado |
|---|---|---|
| **Ingestão dos dados** | `seed/` | ✅ ~5 anos de vendas no Postgres + corpus qualitativo no MinIO/Qdrant, com narrativas plantadas (`seed/NARRATIVAS.md`) |
| **Stack local (docker-compose)** | `docker-compose.yml` | ✅ `postgres` · `qdrant` · `minio` · `api` (FastAPI) · `nginx` |
| **Ambiente git** | `.git`, `.gitignore`, `.env.example` | ✅ repositório configurado |
| **Download das SKILLS** | `skills-lock.json` + `.claude/skills/` | ✅ fontes abaixo |

### Fontes das skills (download)

As skills foram baixadas e travadas em `skills-lock.json` (fonte + `skillPath` + hash de cada uma):

- **Matt Pocock** — skills de processo (`grill-me`, `to-prd`, `to-issues`, `setup-matt-pocock-skills`,
  `tdd`, `diagnose`, `triage`, `handoff`, `write-a-skill`, `zoom-out`…):
  <https://github.com/mattpocock/skills>
- **LangChain / LangGraph / Deep Agents** (`ecosystem-primer`, `langchain-*`, `langgraph-*`,
  `deep-agents-*`, `managed-deep-agents`, `swarm`): <https://github.com/langchain-ai/langchain-skills>
- **FastAPI patterns** (`fastapi-patterns`): <https://github.com/affaan-m/ECC>
- **React** (`react`): <https://github.com/lobehub/lobehub> · **React UI patterns** (`react-ui-patterns`):
  <https://github.com/sickn33/antigravity-awesome-skills>
- **UI/UX Pro Max** (`ui-ux-pro-max`): <https://github.com/nexu-io/open-design>

> **`harness-architect` é skill _própria_ da nossa equipe.** Não veio de fonte externa e por isso
> **não está no `skills-lock.json`** — ela codifica os nossos requisitos de projeto e padrões de
> desenvolvimento, garantindo que o `.claude/` gerado siga *o nosso* padrão (não um template genérico).
> É o ponto central do workshop.

---

## 2. O caminho da ideia às issues (cadeia de skills)

Cada passo abaixo é uma skill (`/comando`). A ordem importa: cada uma consome o artefato da anterior.

| # | Skill | Origem | Entra | Sai | Estado |
|---|---|---|---|---|---|
| 0 | `ideia.md` | — | — | a ideia inicial | ✅ |
| 1 | `/grill-me` | Matt Pocock | `ideia.md` | entendimento afiado | ✅ |
| 2 | `/to-prd` | Matt Pocock | sessão do grill | **`PRD.md`** | ✅ |
| 3 | `/harness-architect` | **nossa equipe** | `PRD.md` | harness em `.claude/` | ▶️ agora |
| 4 | `/setup-matt-pocock-skills` | Matt Pocock | repo + tracker | issue tracker no GitHub | ⬜ |
| 5 | `/to-issues` | Matt Pocock | `PRD.md` | issues *ready-for-agent* | ⬜ |
| 6 | implementar | — | issues | código | ⬜ |

**0. `ideia.md` — a semente.** Documento solto com a ideia inicial do produto. Fica **local e não é
versionado** (não entra no repositório), mas é a origem de toda a cadeia — por isso o mencionamos aqui.

**1. `/grill-me` — interrogar a ideia.** Entrevista o autor sem dó até fechar cada ramo da árvore de
decisões. Não gera arquivo: afia o entendimento que vai alimentar o PRD.

**2. `/to-prd` — consolidar o PRD.** Sintetiza a conversa num PRD, sem nova entrevista.
→ **Output: `PRD.md`** — Problem/Solution, user stories, Implementation/Testing Decisions, Out of Scope.

**3. `/harness-architect` — estruturar o `.claude/`** *(skill própria — centro do workshop)*. Lê o
`PRD.md`, infere o máximo e pergunta só as lacunas (escopo das rules, gate de validação, MCP,
orquestração); depois andaima o harness. → **Output (a ser gerado):** `CLAUDE.md`, `.claude/rules/`,
`.claude/commands/`, `.claude/agents/`, `.claude/settings.json` (hook de gate + permissões) e os ADRs
das decisões contestáveis.

**4. `/setup-matt-pocock-skills` — preparar o tracker.** Depois de **commitar o repositório no GitHub**
(cria o remote que faltava), configura o GitHub como issue tracker e os labels de triagem.

**5. `/to-issues` — fatiar o PRD.** Quebra o `PRD.md` em issues *ready-for-agent* (fatias verticais
tracer-bullet), cada uma independentemente "grabbable".

**6. Implementar.** A partir das issues, o ciclo de implementação roda com gate rápido de validação a
cada edição e os **evals** como gate de aceite.

```bash
# os próximos comandos do workshop, em ordem:
/harness-architect            # andaima o .claude/ a partir do PRD.md   (passo 3)
# ...commit + push do repo para o GitHub...
/setup-matt-pocock-skills     # escolher tracker = GitHub               (passo 4)
/to-issues                    # PRD.md -> issues ready-for-agent         (passo 5)
```

---

## 3. Estrutura atual

Reflete o que está **de fato** no repositório hoje (o harness do passo 3 ainda será gerado):

```
docker-compose.yml     # stack: postgres, qdrant, minio, api (FastAPI), nginx
.env.example           # variáveis (copie para .env antes de subir)
pyproject.toml         # deps (uv) · uv.lock
PRD.md                 # PRD consolidado (output do /to-prd) — base para as issues
skills-lock.json       # lock das skills baixadas (fonte + skillPath + hash)
seed/                  # ingestão: dataset sintético + corpus (offline, sem LLM)
  schema.sql           #   DDL do schema `negocio` (dimensões + fatos + metas)
  generate.py          #   gerador determinístico -> CSVs em seed/data/
  load.py              #   aplica schema + COPY no Postgres (idempotente)
  corpus/              #   docs .md: diagnostico/ e prescricao/ (frontmatter + corpo)
  ingest.py            #   corpus -> MinIO + indexa Qdrant (idempotente)
  NARRATIVAS.md        #   enredo das narrativas plantadas (revisão humana)
  evals/golden/        #   golden dataset derivado
.claude/
  skills/              #   skills baixadas + harness-architect (própria)
                       #   rules/ commands/ agents/ settings.json -> gerados no passo 3
```

---

## 4. Rodar localmente (ingestão)

```bash
cp .env.example .env                          # ajuste os segredos (POSTGRES_PASSWORD etc.)
docker compose up -d postgres qdrant minio    # stores no ar

# 1) Postgres (vendas + metas)
uv run python seed/generate.py                # gera seed/data/*.csv (regenerável; não versionado)
uv run python seed/load.py                    # cria negocio.* e carrega; sanity das narrativas

# 2) Corpus qualitativo (MinIO -> Qdrant)
uv run python seed/ingest.py                  # upload + embed + index; verifica buscas filtradas
```

Consoles: **MinIO** em <http://localhost:9001> · **Qdrant** em <http://localhost:6333/dashboard>.
