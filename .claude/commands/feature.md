---
description: Implementa uma feature pelo fluxo SDD→impl→EDD. Uso: /feature <nome-da-feature>
---
Feature: `$ARGUMENTS`.

1. **Spec (SDD).** Leia/derive o spec em `specs/features/$ARGUMENTS.md` (cenários em BDD/Gherkin a
   partir do `ideia.md` + `DECISOES.md`). Se não existir, crie-o e **confirme o escopo antes de codar**.
2. **Fatia vertical mínima.** Implemente o menor caminho ponta-a-ponta que satisfaz um cenário,
   respeitando as `rules/` da área tocada.
3. **Testes.** Escreva testes (httpx/pytest) do caminho feliz + um erro.
4. **Gate rápido.** Rode `uv run python scripts/gate.py` (ruff + mypy + pytest). Se falhar, corrija
   e repita até verde.
5. **EDD.** Adicione/atualize o caso no golden dataset e rode `/run-evals`. A feature só está
   "pronta" com os evals verdes.
6. **Resumo.** Liste o que mudou, decisões tomadas (vão pra `DECISOES.md`/ADR se contestáveis) e
   próximos passos.
