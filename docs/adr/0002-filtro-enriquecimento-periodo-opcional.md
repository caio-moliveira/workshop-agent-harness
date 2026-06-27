# ADR 0002 — Enriquecimento filtra por kpi_alvo + dimensão; periodo_referencia é opcional

- **Status:** aceito
- **Data:** 2026-06-27
- **Issue:** #35 (tools run_sql + search)

## Contexto

O invariante do produto (CLAUDE.md / `agente.md`) dizia: *enriquecimento Qdrant **sempre
filtrado** por `periodo_referencia` + dimensão + `kpi_alvo`; **nunca** por `data_ingestao`*.

Ao implementar a `search`, os dados reais expõem uma tensão: cada documento de
`prescricao`/`diagnostico` tem um `periodo_referencia` **histórico** (ex.: `2024-08`,
`2025-11`), enquanto o período-alvo do agente é o mês futuro (ex.: `2026-07`). O objetivo do
enriquecimento é recuperar *o que já funcionou* — prescrições de vários períodos passados.
Filtrar por `periodo_referencia = mês-alvo` retornaria **zero** documentos (o golden N1 espera
fontes de 2023, 2024 e 2025).

## Decisão

Interpretamos o invariante pelo seu **espírito**: filtrar pela *família de campos de período
de negócio* (`periodo_referencia`/`ano`/`mes`) e **nunca** por `data_ingestao` — a confusão
entre os dois é o erro que o invariante existe para impedir. O filtro que escopa a recuperação
é **`kpi_alvo` + dimensão** (sempre exigidos). `periodo_referencia` passa a ser **opcional**:
aplicado só quando o nó quer um recorte temporal específico (comparação sazonal por `mes`), não
no caminho "o que funcionou historicamente".

`data_ingestao` segue **proibido em todos os caminhos** (`montar_filtro` e na dimensão).

## Consequências

- N1 recupera as prescrições históricas do Sul; o invariante anti-`data_ingestao` segue forte
  e testado.
- O texto do invariante em `CLAUDE.md` e `.claude/rules/agente.md` foi atualizado para refletir
  "`kpi_alvo` + dimensão sempre; `periodo_referencia` opcional (recorte sazonal)".
- Risco: sem `periodo_referencia` obrigatório, uma busca poderia trazer doc de período
  irrelevante. Mitigado por `kpi_alvo` + dimensão + ranking por similaridade + limite de hits.
