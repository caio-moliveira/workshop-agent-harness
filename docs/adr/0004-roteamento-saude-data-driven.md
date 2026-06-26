# ADR 0004 — Roteamento saudável/fraco data-driven (abaixo da meta = enriquecer)

- **Status:** aceito
- **Data:** 2026-06-26
- **Issue:** #30 (roteamento: separar queda real de sazonalidade)

## Contexto

O grafo precisa decidir, **por dado**, se um KPI merece diagnóstico/prescrição (enriquecer)
ou se é saudável e não vira recomendação corretiva. A regra tem de separar:
- **N3** (conversão do site no inverno): baixa sazonal **abaixo do alvo absoluto**, recorrente
  — o golden manda **enriquecer** (é deficit acionável).
- **N6** (ticket médio sobe no Q4): alta sazonal **acima/no alvo** — **não** enriquece (a alta
  é esperada e boa, não um deficit).
- **N4** (Beleza/Nordeste acima da meta): saudável — **não** enriquece.

## Decisão

O gate de roteamento é **estar abaixo da meta**, não a sazonalidade:

- **Fraco (enriquece)** = valor recente **< meta** (deficit), *independente* de a queda ser
  sazonal ou não — estar abaixo do alvo é o problema. Cobre N1/N3/N5.
- **Saudável (não enriquece)** = no/acima da meta. Cobre N4 e N6 (a variação, inclusive a alta
  sazonal, não é deficit).
- **Sem meta cadastrada:** cai no comparativo sazonal — fraco só se houver **queda real** (pior
  que todos os anos anteriores).

A distinção "queda real × variação sazonal" exigida pelo PRD vive no **diagnóstico** (o nó
`relatorio` recebe tendência + sazonal e o LLM explica a causa), e como um flag informativo
`parece_sazonal` no veredito de saúde — **não** no gate de roteamento.

## Consequências

- Roteamento determinístico, testável, sem LLM — aresta condicional no grafo (código decide,
  não o LLM solto), compatível com o invariante de determinismo.
- N4/N6 deixam de disparar enriquecimento; N1/N3/N5 continuam enriquecendo.
- Requer a **meta** no resultset da perna quantitativa (query `meta` adicionada aos templates).
- Limite: depende de a meta existir e ser coerente; sem meta, o fallback sazonal é mais frouxo.
