---
description: Regras ao editar o agente (grafo LangGraph, nós e tools). Aplica a backend/app/agent/**.
---
# Agente (LangGraph — grafo determinístico)

- O grafo é **determinístico**: arestas fixas
  `planejar → perna_quantitativa → (por KPI fraco: diagnostico → prescricao) → sintese → relatorio`.
  O fan-out é por KPI fraco (**data-driven**), não por o LLM escolher ramificar. Sem ReAct livre.
- O LLM decide **só dentro de um nó**, em escopo fechado: traduzir pergunta→KPIs (consultando
  `camada_semantica`), gerar SQL, escolher dimensão a aprofundar, redigir narrativa.
- Exatamente **2 tools**: `run_sql` (Postgres RO) e `search(collection, query, filters)`
  (Qdrant; a coleção — `camada_semantica` | `diagnostico` | `prescricao` — é escolhida pelo **nó**,
  não pelo LLM). **Não crie uma tool por coleção.**
- **Chat:** cada turno passa por reescrita contextual ("condense question") → roteador de intenção
  → sub-grafo. O sub-grafo analítico é **stateless**; o estado de sessão vai pro schema de harness.
- **Grounding:** o nó de síntese só roda após nós de recuperação; nenhuma recomendação sai sem fonte.
- Tool nova = contrato base + registro no grafo + eval cobrindo feliz/erro + gates verdes.
