---
description: (Re)gera o dataset sintético, as narrativas plantadas e os itens de golden dataset.
---
1. (Re)gere o dataset de **e-commerce sintético** em `seed/` com 2+ anos de histórico e
   sazonalidade, nas dimensões região × canal × categoria.
2. Garanta as **5–8 narrativas plantadas** (triplo rastreável): padrão quantitativo no Postgres ↔
   documentos de `diagnostico` ↔ documentos de `prescricao` com `resultado`
   (inclua **≥1 par funcionou / não-funcionou** para o contraste da síntese).
3. Para cada narrativa, gere/atualize ≥1 item no golden dataset (`evals/golden/`) com `pergunta`,
   `sql_esperado`, `fontes_esperadas`, `recomendacao_esperada`.
4. Carregue vendas+metas no Postgres e suba os documentos pela ingestão (MinIO→Qdrant) —
   **sem** acionar o agente.
5. Documente cada narrativa (o "enredo") em `seed/NARRATIVAS.md` para revisão humana.
