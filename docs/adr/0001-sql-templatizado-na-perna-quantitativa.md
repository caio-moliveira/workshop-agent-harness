# ADR 0001 — SQL templatizado (não text-to-SQL livre) na perna quantitativa

- **Status:** aceito
- **Data:** 2026-06-26
- **Contexto da issue:** #29 (grafo determinístico + /chat SSE)

## Contexto

A `perna_quantitativa` do grafo precisa medir cada KPI fraco em três janelas (tendência
dos últimos 6 meses, sazonal do mesmo mês em anos anteriores, e a meta). Há duas formas
de produzir o SQL:

1. **text-to-SQL livre:** o LLM gera o SQL a partir da pergunta + `camada_semantica`.
2. **templates determinísticos:** SQL parametrizado por `kpi_alvo` + dimensão, montado por
   código; o LLM só escolhe *o que* investigar (KPI/dimensão), não *como* consultar.

## Decisão

Adotamos **templates determinísticos por KPI** nesta fatia. O domínio tem exatamente 4
KPIs (`faturamento`, `ticket_medio`, `taxa_recompra`, `taxa_conversao`); cada um tem um
template de tendência/sazonal/meta, parametrizado pela dimensão (região/canal/categoria).
Todo SQL ainda passa pelos guardrails do `run_sql` e pelo papel `agente_ro` (#28).

## Consequências

**A favor**
- Honra o invariante **grafo determinístico**: o mesmo input gera o mesmo SQL e o mesmo
  resultset — pré-requisito do golden dataset e dos evals (execution accuracy).
- Elimina a classe de falha "LLM gerou SQL inválido/perigoso" no caminho quente.
- Resultados auditáveis: o analista vê um SQL estável e conhecido.

**Contra / limites**
- Cobre só os 4 KPIs e as dimensões previstas; perguntas fora desse recorte não viram
  consulta nova automaticamente.
- O LLM ainda decide KPI/dimensão (dentro do nó `planejar`) — essa parte não é determinística,
  mas é estruturada (saída validada) e mockável em teste.

## Alternativa adiada

text-to-SQL livre via LLM, ancorado na `camada_semantica` (exemplos pergunta→SQL já
indexados), fica para uma fatia futura quando houver um avaliador que barre SQL incorreto
antes de promover. Até lá, o ganho de flexibilidade não paga o custo de determinismo.
