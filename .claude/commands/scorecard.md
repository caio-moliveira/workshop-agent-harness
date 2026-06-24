---
description: Gera o scorecard de entrega (correção, aderência, throughput, autonomia) p/ o time e stakeholders.
argument-hint: "[--desde <data|tag>] [--issue <N>]"
---

# /scorecard — scorecard de entrega

Mede a execução do Claude Code contra a [Definição de Pronto](../rules/definicao-de-pronto.md) e
produz um relatório que um líder/stakeholder entende sem abrir o código. **Não** mede a qualidade da
resposta do produto (isso seria eval de produto) — mede se as **issues foram implementadas certo e
no padrão**.

## 1. Colete os dados (fonte da verdade = git + gh; o agente não forja)
- **git:** `git log --oneline`, autores e datas (`git log --format=...`), `git diff --stat` por
  issue. Issues aparecem como `feat(#N): ...` nos commits.
- **gh:** `gh issue list --state all --json number,title,state,createdAt,closedAt,labels` e
  `gh pr list --state all --json number,reviewDecision,reviews,additions,deletions`. Se `gh` não
  estiver autenticado, **diga isso** e siga com o que der.
- **metrics/entregas.jsonl:** um registro por issue (gate, revisor, critérios). Se vazio, reporte
  as métricas derivadas de git/gh e marque as de sessão como "sem dado".

## 2. Calcule (apenas o que tem dado — nunca invente número)
- **Correção:** % de critérios de aceite atendidos · **change-failure rate** = (issues reabertas +
  bugs contra issue merjada + PRs com mudança pedida) ÷ issues entregues.
- **Aderência ao padrão:** distribuição de veredito do revisor (aprovado/ressalva/bloqueado) ·
  invariantes violados · média de tentativas até o gate verde.
- **Throughput:** lead time por issue (criada → fechada/merge) · issues concluídas no período.
- **Confiança:** taxa de autonomia (% merjado sem edição humana) · ações barradas por permissão/hook.

## 3. Emita o scorecard (markdown, pronto pra colar num board)

```
# Scorecard de entrega — <período>

## Resumo (agregado)
| Métrica | Valor | Tendência |
|---|---|---|
| Critérios de aceite atendidos | 96% (24/25) | ▲ |
| Change-failure rate | 8% (1/13) | ▼ bom |
| Taxa de autonomia | 77% (10/13) | ▲ |
| Lead time mediano | 1.4 dia | — |
| Revisor: aprovado / ressalva / bloqueado | 9 / 3 / 1 | — |
| Tentativas medianas até o gate verde | 2 | ▼ bom |

## Por issue
| # | Título | Aceite | Gate (tent.) | Revisor | Lead time | Autônoma |
|---|---|---|---|---|---|---|
| 23 | streaming SSE | 4/4 | verde (2) | aprovado | 1.1d | sim |
...

## Leitura para stakeholders
- 2–4 linhas em português claro: o que está sólido, onde está o risco, o que puxar pra próxima sprint.
```

## 4. Seja honesto sobre lacunas
Se faltou dado (sem `gh` auth, `entregas.jsonl` vazio, período sem issues fechadas), **declare
explicitamente o que não pôde ser medido** — um scorecard que finge cobertura é pior que um com
buracos assumidos.
