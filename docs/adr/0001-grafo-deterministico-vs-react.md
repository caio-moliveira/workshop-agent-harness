# ADR 0001: Grafo determinístico em vez de loop ReAct

## Contexto
O runtime é um agente LangGraph. "Agente" frequentemente sugere um loop ReAct, onde o LLM escolhe
livremente qual tool chamar até decidir que terminou. O PRD descreve um fluxo de 8 passos (§9) que
já lê como pipeline, e exige EDD-first (§12–13), observabilidade e reprodutibilidade (RNF-04/05).

## Decisão
O grafo é majoritariamente determinístico: arestas fixas
`planejar → perna_quantitativa → (por KPI fraco: diagnostico → prescricao) → sintese → relatorio`.
O fan-out é data-driven (nº de KPIs fracos). O LLM decide só dentro de nós, em escopo fechado.
Sem ReAct livre.

## Alternativas consideradas
- **ReAct livre:** mais flexível para perguntas fora do trilho, mas difícil de avaliar com golden
  dataset, trace imprevisível, latência aberta e grounding mais frágil.
- **Sub-agente autônomo por KPI:** adia complexidade sem ganho claro no MVP.

## Consequências
- (+) Eval por etapa; trace reprodutível; grounding fácil de garantir; o grafo é didático (workshop).
- (−) Menos "esperto" em perguntas fora do caso central — aceitável, é não-objetivo (§3.2).
- Registrada como **D4** em `DECISOES.md`.
