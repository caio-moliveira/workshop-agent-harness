# ADR 0003: EDD ancorado em narrativas plantadas

## Contexto
A tese do produto é cruzar o *o quê* (Postgres) com o *porquê / o que fazer* (Qdrant). Num dataset
sintético, essa relação não emerge sozinha — precisa ser projetada. Sem isso, o golden dataset não
tem fontes esperadas defensáveis e o agente não tem o que "descobrir".

## Decisão
O dataset é construído em torno de **5–8 narrativas plantadas**, cada uma um triplo rastreável
(padrão quantitativo no Postgres ↔ documentos de diagnóstico ↔ prescrição com `resultado`). Cada
narrativa gera ≥1 item de golden dataset. O EDD nasce das narrativas e roda como gate de aceite.

## Alternativas consideradas
- **Dados aleatórios + corpus genérico:** o agente não teria o que descobrir; evals sem ground truth.
- **Só dados reais de um cliente:** fora de escopo do workshop e com risco de PII.

## Consequências
- (+) Ground truth defensável; demo convincente; evals significativos.
- (−) Curadoria manual das narrativas (esforço inicial, mitigado por `/seed-data`).
- Registrada como **D3 + D10** em `DECISOES.md`.
