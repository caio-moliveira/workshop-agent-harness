# metrics/ — rastro de entrega do time

Métricas de **execução** (o Claude Code implementou bem as issues?) — não confundir com evals de
produto (o agente responde bem?). O `/scorecard` lê esta pasta + `git`/`gh` e gera o
relatório para o time e stakeholders.

## `entregas.jsonl`

Um objeto JSON **por linha**, um por issue concluída. Gravado ao fechar a issue (ver a
[Definição de Pronto](../.claude/rules/definicao-de-pronto.md)). Guarda os sinais que o `git` não
enxerga (tentativas até o gate verde, veredito do revisor, critérios de aceite).

Schema de cada linha:

```json
{
  "issue": 23,
  "titulo": "streaming SSE no /chat",
  "data": "2026-06-24",
  "criterios_aceite": { "total": 4, "atendidos": 4 },
  "gate": { "resultado": "verde", "tentativas_ate_verde": 2 },
  "revisor": { "veredito": "aprovado", "bloqueantes": 0, "ressalvas": 1 },
  "intervencoes_humanas": 0,
  "commit": "5c0af2a"
}
```

- `veredito`: `aprovado` · `aprovado com ressalvas` · `bloqueado`.
- `gate.resultado`: `verde` · `vermelho`. `tentativas_ate_verde`: quantas rodadas o gate reprovou
  antes de passar (alto = agente brigando com o padrão).
- `intervencoes_humanas`: quantas vezes um humano precisou editar/corrigir antes do merge.

O que é lead time, reabertura, autonomia (autor do commit) e mudança pedida em PR **não** vai aqui
— o `/scorecard` deriva isso direto de `git log` e `gh`, que o agente não consegue forjar.
