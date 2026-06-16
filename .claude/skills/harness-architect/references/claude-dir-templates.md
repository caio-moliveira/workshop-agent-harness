# Templates do `.claude/`

Use estes esqueletos ao andaimar. Preencha com o que saiu do Harness Plan. Gere só o que o plano
pediu. Cada arquivo declara, no topo ou em comentário, qual pergunta responde.

---

## `CLAUDE.md` (raiz) — "o que vale para o projeto inteiro?"

Mantenha enxuto (idealmente < 500 tokens). É um índice de fatos duráveis, não documentação.

```markdown
# [Projeto] — guia do agente

## Stack
[linguagens, frameworks, stores — uma linha]

## Comandos
- rodar: `...`
- testar: `...`
- validar (gates): `...`

## Invariantes (nunca quebrar)
- [ex.: toda query ao banco de negócio é SOMENTE LEITURA]
- [ex.: o agente nunca escreve no schema de negócio]
- [ex.: ingestão e runtime são fases separadas; não misture]

## Onde fica o quê
- regras por área: `.claude/rules/`
- decisões e porquês: `docs/adr/`
- avaliação: `evals/`
```

---

## `rules/<area>.md` — "o que lembrar ao mexer nesta área?"

Uma regra curta, carregada nativamente de `.claude/rules/`. **Sem `paths:`** ela vale a sessão
inteira; **com `paths:`** (globs) carrega só quando o agente toca arquivos daquela área — prefira
isso para manter o contexto enxuto.

```markdown
---
description: Regras ao editar o backend
paths:
  - "backend/**"
---
- Toda tool nova segue o contrato de `harness/tools/base.py`.
- SQL passa pelo guardrail antes de executar (read-only, allowlist, LIMIT, timeout).
- Não edite `infra/db/migrations/` sem revisão humana.
```

Regra que vale o projeto todo (invariante de área única) é só omitir o `paths:`.

---

## `skills/<nome>/SKILL.md` — "como fazer esta operação repetível do jeito do projeto?"

Skill é uma pasta. A frontmatter (`name`, `description`) controla o disparo.

```markdown
---
name: new-harness-tool
description: Cria uma nova tool do agente no padrão do projeto. Use ao adicionar uma capacidade
  nova ao agente (busca, query, exportação).
---
# Criar uma tool de harness
1. Crie `harness/tools/<nome>.py` herdando de `base.py`.
2. Registre no tool registry do grafo LangGraph.
3. Adicione um eval em `evals/` cobrindo o caminho feliz e um erro.
4. Rode os gates (`...`) e garanta verde.
```

---

## `agents/<nome>.md` — "que tarefa delegar a um contexto fresco?"

Subagente. Use para isolar trabalho que poluiria o contexto principal.

```markdown
---
name: eval-runner
description: Roda a suíte de avaliação e devolve só o veredito (passou/falhou + falhas).
tools: Bash, Read
---
Rode `python evals/run_evals.py`, leia o resultado e responda apenas com o resumo:
quais evals falharam e por quê. Não tente corrigir o código.
```

**Boas práticas (Anthropic):** `description` em 3ª pessoa com gatilho ("Use quando…"); `tools` no
mínimo necessário (um avaliador é read-only: `Read, Grep, Bash`); **uma responsabilidade só**;
declare o formato de saída ("devolva só o veredito") e o que NÃO fazer ("não corrija código").

---

## `commands/<nome>.md` — "qual sequência de passos eu repito?"

Comando slash. Pode orquestrar skills e subagentes.

```markdown
---
description: Implementa uma feature seguindo o Feature Flow
---
1. Leia o spec da feature em `specs/features/$ARGUMENTS.md`.
2. Implemente a fatia vertical mínima.
3. Acione a skill de teste e rode os gates.
4. Se um gate falhar, corrija e repita (loop até verde).
5. Abra um resumo do que mudou.
```

**Boas práticas (Anthropic):** `description` numa linha; corpo = passos numerados usando
`$ARGUMENTS`; delegue a skills/subagentes em vez de repetir lógica; termine sempre num gate
(validação) ou num resumo.

---

## `settings.json` — "o que sempre roda? o que o agente pode fazer sozinho?"

Hooks (gates de validação) + permissões (perímetro), e opcionalmente `env`/`model` do projeto.
Permissões têm três tiers: `allow`, `ask` (pede confirmação) e `deny`.

```json
{
  "model": "sonnet",
  "env": { "PYTHONUNBUFFERED": "1" },
  "permissions": {
    "allow": ["Bash(npm test:*)", "Bash(ruff:*)", "Read", "Edit"],
    "ask": ["Bash(git push:*)"],
    "deny": ["Bash(rm -rf:*)", "Edit(infra/db/migrations/**)"]
  },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "scripts/guard.sh" }] }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "ruff check --fix . && mypy . && pytest -q" }]
      }
    ],
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "scripts/session_setup.sh" }] }
    ]
  }
}
```

- **`PreToolUse`** roda *antes* da ferramenta e pode **bloquear** (exit code 2 nega a ação) —
  guardrail determinístico (ex.: barrar comando perigoso). **`PostToolUse`** roda depois (gate de
  lint/types/testes). **`SessionStart`** prepara contexto no início. Há outros eventos
  (UserPromptSubmit, Stop, PreCompact…); use só os que o projeto precisa.
- **`settings.local.json`** (ao lado, gitignored, mesmo formato) guarda *overrides pessoais* de
  máquina — não versione segredos nem preferências individuais no `settings.json` do projeto.

---

## `.mcp.json` — "que infra o agente precisa enxergar?"

Servidores MCP para o agente inspecionar stores reais durante a construção.

```json
{
  "mcpServers": {
    "postgres": { "command": "...", "args": ["..."] },
    "qdrant": { "command": "...", "args": ["..."] }
  }
}
```

---

## `docs/adr/NNNN-titulo.md` — "por que decidimos isto?"

Architecture Decision Record. Registra o porquê, não só o resultado.

```markdown
# ADR NNNN: [decisão]
## Contexto
## Decisão
## Alternativas consideradas
## Consequências
```

---

## `HANDOFF.md` — "como o próximo agente continua de onde parei?"

Template de handoff de sessão.

```markdown
# Handoff — [data]
## Objetivo da sessão
## O que foi feito
## Estado atual (verde/vermelho nos gates)
## Próximos passos
## Armadilhas / contexto que não está óbvio no código
```

---

## Nota sobre `MEMORY.md` (nível usuário)

Além dos arquivos no repositório, o agente pode manter notas para si em
`~/.claude/projects/.../MEMORY.md`, carregadas no início de cada sessão. Isso é memória de
nível usuário, fora do repo — mencione ao usuário, mas não a versione no `.claude/` do projeto.