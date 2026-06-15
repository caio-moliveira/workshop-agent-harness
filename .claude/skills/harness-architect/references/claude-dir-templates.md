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

Uma regra curta, path-scoped. Frontmatter opcional para escopo por caminho.

```markdown
---
description: Regras ao editar o backend
---
- Toda tool nova segue o contrato de `harness/tools/base.py`.
- SQL passa pelo guardrail antes de executar (read-only, allowlist, LIMIT, timeout).
- Não edite `infra/db/migrations/` sem revisão humana.
```

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

---

## `settings.json` — "o que sempre roda? o que o agente pode fazer sozinho?"

Hooks (gates de validação) + permissões (perímetro). Estrutura de hooks por evento e matcher.

```json
{
  "permissions": {
    "allow": ["Bash(npm test:*)", "Bash(ruff:*)", "Read", "Edit"],
    "deny": ["Bash(rm -rf:*)", "Edit(infra/db/migrations/**)"]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "ruff check --fix . && mypy . && pytest -q" }
        ]
      }
    ]
  }
}
```

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