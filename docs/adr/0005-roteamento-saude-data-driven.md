# ADR 0005 — Roteamento saudável/fraco data-driven (abaixo da meta = enriquecer)

- **Status:** aceito
- **Data:** 2026-06-27
- **Issue:** #37 (roteamento: separar queda real de sazonalidade)

## Contexto

O grafo precisa decidir, **por dado**, se um KPI merece diagnóstico/prescrição (enriquecer)
ou se é saudável e não vira recomendação corretiva. A regra tem de separar:
- **N3** (conversão no inverno): baixa sazonal **abaixo do alvo**, recorrente — **enriquece**.
- **N6** (ticket sobe no Q4): alta sazonal **acima/no alvo** — **não** enriquece.
- **N4** (Beleza/Nordeste acima da meta): saudável — **não** enriquece.

## Decisão

O gate de roteamento é **estar abaixo da meta**, não a sazonalidade:

- **Fraco (enriquece)** = valor recente **< meta** (deficit), *independente* de a queda ser
  sazonal — estar abaixo do alvo é o problema. Cobre N1/N3/N5.
- **Saudável (não enriquece)** = no/acima da meta. Cobre N4 e N6.
- **Sem meta cadastrada:** comparativo sazonal — fraco só se houver **queda real** (pior que
  todos os anos anteriores).

A distinção "queda real × variação sazonal" exigida pelo PRD vive no **diagnóstico** (o nó
`relatorio` recebe tendência + sazonal e o LLM explica a causa), e como flag informativo
`parece_sazonal` no veredito — **não** no gate de roteamento.

## Consequências

- Roteamento determinístico, testável, sem LLM — aresta condicional no grafo (código decide).
- N4/N6 deixam de disparar enriquecimento; N1/N3/N5 continuam enriquecendo.
- Requer a **meta** no resultset da perna quantitativa. Como o mês-alvo é futuro e pode não ter
  meta, usa-se a meta **mais recente ≤ alvo** como referência.
