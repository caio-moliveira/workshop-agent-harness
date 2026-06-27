# ADR 0004 — SQL templatizado (não text-to-SQL livre) na perna quantitativa

- **Status:** aceito
- **Data:** 2026-06-27
- **Issue:** #36 (grafo determinístico + /chat SSE)

## Contexto

A `perna_quantitativa` mede cada KPI em janelas (tendência dos últimos 6 meses, sazonal do
mesmo mês em anos anteriores). Há duas formas de gerar o SQL: (1) **text-to-SQL livre** (o LLM
gera o SQL) ou (2) **templates determinísticos** por KPI (o LLM só escolhe *o que* investigar).

## Decisão

**Templates determinísticos por KPI.** O domínio tem 4 KPIs; cada um tem um template de
tendência/sazonal parametrizado pela dimensão. Todo SQL passa pelos guardrails do `run_sql` e
pelo papel `agente_ro`.

## Consequências

- Honra o invariante **grafo determinístico**: mesmo input → mesmo SQL → mesmo resultset
  (pré-requisito do golden/eval e da execution accuracy).
- Elimina a classe de falha "LLM gerou SQL inválido/perigoso" no caminho quente.
- Cobre só os 4 KPIs e as dimensões previstas. text-to-SQL livre fica para uma fatia futura,
  quando houver avaliador que barre SQL incorreto antes de promover.
