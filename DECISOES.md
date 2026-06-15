# Registro de Decisões — Bússola (Agente Analítico de Vendas)

> Companion do `ideia.md`. Fecha as questões em aberto da seção 15 e as decisões
> arquiteturais levantadas na sessão de grilling. Cada decisão tem o porquê e,
> quando aplicável, a marca **(refinável)** para o que pode mudar na fase de SPEC.
>
> **Data:** 15 de junho de 2026 · **Status:** decisões fechadas, base para o SPEC.

---

## D1 — Propósito do projeto

Workshop **conduzido como um projeto de mundo real**: simulamos o build completo
de ponta a ponta. **Aceite duplo:** (a) a arquitetura e os evals demonstram o
padrão de forma exemplar; (b) o resultado é convincente como produto real
(domínio plausível, corpus crível, relatório que um gestor levaria a sério).

## D2 — Domínio do dataset

**E-commerce de varejo genérico**, multicanal (site próprio + marketplace + loja
física), multi-região (Sul, Sudeste, …) e com **clientes recorrentes** (recompra
é KPI de primeira classe). Categorias de produto concretas ficam para a fase de
schema. **(refinável: vertical específico)**

## D3 — Espinha dorsal dos dados: narrativas plantadas

O dataset sintético tem **5 a 8 narrativas plantadas**, cada uma um *triplo
rastreável*:

1. **Padrão quantitativo** no Postgres (ex.: recompra no Sul cai 18% no Q1 vs. sazonal);
2. **Documentos de diagnóstico** no Qdrant que explicam o porquê (ex.: pico de
   tickets de atraso após troca de transportadora no Sul);
3. **Documentos de prescrição com `resultado`** (ex.: campanha de frete grátis no
   Sul no ano anterior — `resultado: positivo`; mais ao menos um par
   "funcionou / não funcionou" para alimentar o contraste do passo 7).

Cada narrativa vira **um item do golden dataset** (pergunta → SQL esperado →
fontes esperadas → recomendação esperada). **O EDD nasce das narrativas.** O
restante do dataset é ruído realista de fundo, com KPIs saudáveis que **não**
disparam enriquecimento (testa o roteamento do passo 4).

## D4 — Arquitetura do runtime: grafo determinístico

Agente em LangGraph como **grafo majoritariamente determinístico**, *não* um loop
ReAct livre:

- **Arestas fixas:** `planejar → perna_quantitativa → (por KPI fraco: diagnóstico
  → prescrição) → síntese → relatório`.
- **Fan-out data-driven:** o número de investigações = número de KPIs abaixo da
  meta. O *dado* ramifica, não o LLM.
- **LLM decide dentro dos nós**, em escopo fechado: traduzir pergunta vaga em
  KPIs, gerar SQL, escolher a dimensão a aprofundar, redigir a narrativa.

Motivo: eval por etapa (não só end-to-end), trace reprodutível (RNF-04/05),
grounding mais fácil de garantir (RNF-02), e o grafo *é a aula* do workshop.

## D5 — Interface: chat multi-turno

Produto é um **chat**. Sobre o sub-grafo analítico (D4, *stateless*) há uma
**porta de entrada conversacional**:

- **Roteador de intenção:** caso central (5.1) → pipeline pesado; casos
  secundários (5.2) → caminhos mais leves; conversa/clarificação → resposta direta.
- **Reescrita contextual da pergunta** ("condense question"): cada turno é
  reescrito numa pergunta autônoma usando o histórico, e *então* roteado.
- **Estado de sessão** (sessões, runs, turnos) no **schema de harness** do
  Postgres. Sem memória de longo prazo entre sessões no MVP.

## D6 — Comportamento sob ambiguidade

**Best-effort com premissas declaradas.** O agente não trava esperando input:
resolve a ambiguidade com defaults sensatos (período-alvo = mês atual + 1; escopo
= todos os KPIs com meta definida) e **declara as premissas no topo do
relatório**. Exceção: faz **uma** pergunta de volta apenas quando *nem o período
nem nenhum KPI* forem resolvíveis. Premissas declaradas são auditáveis e alinham
com o grounding.

## D7 — Janelas temporais

- **Tendência:** últimos **6 meses**.
- **Sazonal:** o mesmo mês-alvo nos **2 anos anteriores**.

Casa com a premissa de "2+ anos de histórico". Parametrizável via config; defaults
acima são os cravados. **(refinável)**

## D8 — Tools do agente

Duas tools, com naturezas distintas:

- **`run_sql`** — Postgres, somente leitura, com guardrails determinísticos
  (usuário read-only, allowlist de tabelas, `LIMIT` forçado, timeout) + query-checker
  por LLM como camada soft (RNF-01).
- **`search(collection, query, filters)`** — Qdrant, **tool única parametrizada
  pela coleção** (`camada_semantica` | `diagnostico` | `prescricao`). A coleção é
  escolhida pelo **nó do grafo**, não pelo LLM num laço. Menos superfície, mais
  fácil de testar.

(Fecha a questão da seção 15 sobre "tool por coleção vs. única parametrizada".)

## D9 — Modelo de LLM

Default **Claude** (mais recente): tier forte (Opus/Sonnet 4.x) para
planejamento e síntese; tier rápido para geração de SQL e roteamento; modelo de
**embedding dedicado** na ingestão. A arquitetura é *provider-agnostic* (LangChain),
então o modelo é trocável. **(refinável)**

## D10 — Avaliação (EDD)

- **Golden dataset versionado fora do backend** (YAML/JSON), derivado das
  narrativas plantadas (D3).
- **Runner em pytest** rodando como **gate de aceite** a cada entrega.
- **Execution accuracy:** determinística — compara o resultset do SQL gerado com
  o esperado.
- **Faithfulness** e **answer relevancy:** via LLM-as-judge (deepeval/ragas ou
  harness próprio). **(refinável: ferramenta)**

## D11 — Latência alvo

- Relatório completo (caso central): **≤ ~30s p95**, com **streaming** da
  resposta para a UX do chat.
- Casos secundários (5.2): **≤ ~10s**.

Alvos para ter o que medir (RNF-06); calibráveis após a primeira medição.
**(refinável)**

---

## Questões da seção 15 — status

| Questão em aberto | Resolução |
|---|---|
| Dataset sintético genérico ou domínio específico? | D2 — e-commerce de varejo genérico |
| Tamanho das janelas (tendência / sazonal)? | D7 — 6 meses / 2 anos |
| Enriquecimento: tool por coleção ou única parametrizada? | D8 — única parametrizada (`search`) |
| Metas de latência? | D11 — 30s p95 (central) / 10s (secundários) |

## Próximos passos (atualiza a seção 16 do `ideia.md`)

1. ~~Fechar as questões da seção 15~~ → feito (este documento).
2. Derivar o **SPEC** (SDD) a partir do PRD + estas decisões, com features em BDD/Gherkin.
3. Definir o **schema concreto do Postgres** (vendas + metas + harness) e o
   **payload final** de cada coleção do Qdrant.
4. Projetar as **5–8 narrativas plantadas** e montar o **golden dataset inicial**.
5. Estruturar o **harness de construção** (`.claude/`: CLAUDE.md, skills, hooks,
   commands) para conduzir a implementação via agente de código.
