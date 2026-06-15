---
description: Regras ao editar a avaliação (EDD). Aplica a evals/**.
---
# Avaliação (Eval-Driven Development)

- A avaliação é **cidadã de primeira classe e fica FORA do código do backend**.
- Golden dataset em **YAML/JSON versionado**, derivado das **narrativas plantadas**: cada narrativa
  gera ≥1 item com `pergunta`, `sql_esperado`, `fontes_esperadas`, `recomendacao_esperada`.
- Métricas:
  - **execution accuracy** — determinística: compara o resultset do SQL gerado com o esperado;
  - **faithfulness** e **answer relevancy** — via LLM-as-judge.
- Os evals rodam **sob comando** (`/run-evals`), **não** no hook de cada edição, e são
  **gate de aceite** de feature.
- Ao adicionar/alterar uma feature, ajuste o caso de eval correspondente **antes** de chamar de "pronto".
