# ADR 0003 — Execution accuracy do eval: validade do golden + validade do SQL do agente

- **Status:** aceito
- **Data:** 2026-06-26
- **Issue:** #33 (gate de avaliação EDD)

## Contexto

A issue #33 pede "execution accuracy: comparar o resultset do SQL **que o agente gerou**
com o `sql_esperado`". Isso pressupõe que o agente faz **text-to-SQL** e produz uma query
comparável à canônica do golden. Mas, pela **ADR 0001**, o agente usa **SQL templatizado**
(tendência + sazonal por KPI), com *shape* diferente da query única do golden (ex.: N1 gold
devolve a `taxa_recompra` mensal de 2026; o template devolve duas séries). Uma igualdade
estrita de resultset entre os dois daria ~0% — métrica enganosa, não um sinal de qualidade.

## Decisão

Enquanto o agente não fizer text-to-SQL, **execution accuracy** é medida como duas validades:

1. **Validade do golden:** roda-se o `sql_esperado` ao vivo (via `run_sql`, papel RO) e
   exige-se resultset **não-vazio** — garante que o gabarito continua coerente com os dados
   semeados (contrato golden↔dados).
2. **Validade do SQL do agente:** a perna quantitativa do agente (templates) **executa** pelos
   guardrails e retorna linhas para itens não-controle.

O **foco do gate** recai sobre os sinais que medem de fato a qualidade nesta arquitetura:
**grounding** (fontes citadas ⊆ esperadas, sem distratores), **routing** (controles N4/N6 não
enriquecem) e **faithfulness/answer-relevancy** (LLM-as-judge).

## Consequências

- O eval mede o que é significativo hoje e não finge uma acurácia text-to-SQL que o agente
  não tenta. `comparadores.resultsets_iguais` fica disponível para quando text-to-SQL chegar.
- Gaps reais ficam visíveis e medidos (ex.: dimensão `categoria` ainda sem template; routing
  de KPI saudável é a #30) — o gate aponta exatamente o que falta, em vez de mascarar.
- Quando text-to-SQL livre entrar (alternativa adiada na ADR 0001), promove-se a comparação
  estrita agente-vs-gold como execution accuracy plena.
