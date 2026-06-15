---
description: Roda a suíte de avaliação (EDD) em contexto fresco e devolve o veredito.
---
Delegue ao subagente `eval-runner` (contexto fresco, não polui o principal). Repasse o veredito:
quais evals passaram/falharam, as métricas (execution accuracy, faithfulness, answer relevancy) e,
nas falhas, o motivo provável. **Não corrija código aqui** — só reporte; a correção é decisão do
fluxo principal (`/feature`).
