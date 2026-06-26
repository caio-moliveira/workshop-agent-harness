# ADR 0002 — Enriquecimento filtra por kpi_alvo + dimensão; periodo_referencia é opcional

- **Status:** aceito
- **Data:** 2026-06-26
- **Issues:** #29 (ajusta o contrato da tool `search` entregue na #28)

## Contexto

O invariante do produto (CLAUDE.md / `agente.md`) diz: *enriquecimento Qdrant **sempre
filtrado** por `periodo_referencia` + dimensão + `kpi_alvo`; **nunca** por `data_ingestao`
(`periodo_referencia ≠ data_ingestao`)*.

Ao implementar o nó `enriquecer` (#29), os dados reais expuseram uma tensão: cada documento
de `prescricao`/`diagnostico` tem um `periodo_referencia` **histórico** (ex.: `2024-08`,
`2025-11`), enquanto o período-alvo do agente é o mês futuro (ex.: `2026-07`). O objetivo do
enriquecimento é justamente recuperar *o que já funcionou* — prescrições de vários períodos
passados. Filtrar por `periodo_referencia = mês-alvo` retornaria **zero** documentos, e o
golden N1 espera fontes de 2023, 2024 e 2025.

## Decisão

Interpretamos o invariante pelo seu **espírito**: filtrar pela *família de campos de período
de negócio* (`periodo_referencia`/`ano`/`mes`) e **nunca** por `data_ingestao` — a confusão
entre os dois é o erro que o invariante existe para impedir. O filtro que escopa a recuperação
ao caso é **`kpi_alvo` + dimensão** (sempre exigidos). `periodo_referencia` passa a ser
**opcional**: aplicado só quando o nó quer um recorte temporal específico (ex.: comparação
sazonal por `mes`), não no caminho "o que funcionou historicamente".

Mudança concreta na tool `search` (#28):
- `buscar_enriquecimento`: `kpi_alvo` + `dimensão` obrigatórios; `periodo_referencia` opcional;
  `data_ingestao` proibido em qualquer caminho (inalterado).
- `buscar` (genérico): para coleções de enriquecimento exige `kpi_alvo` (antes exigia também
  `periodo_referencia`).

## Consequências

- O N1 recupera as prescrições históricas do Sul (frete grátis 2024/2023, brinde 2025) e o
  diagnóstico de atrasos (2025-11) — como o golden espera.
- O invariante anti-`data_ingestao` segue **forte** e testado.
- Testes da #28 atualizados para o novo contrato (não é regressão: é correção do contrato).
- Risco: sem `periodo_referencia` obrigatório, uma busca poderia trazer doc de período
  irrelevante. Mitigado por `kpi_alvo` + dimensão + ranking por similaridade + limite de hits.
