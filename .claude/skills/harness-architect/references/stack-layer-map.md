# Mapa stack → artefato

Lente para o passo 1: leia o PRD **por camada** e, para cada camada que o PRD realmente prevê,
derive os artefatos abaixo. Camada ausente no PRD **não vira arquivo**. Mantenha cada regra curta e
path-scoped; um `agent` só nasce quando há trabalho delegável de contexto fresco.

| Camada | `rules/` típico (curto, por área) | `agents/` (só se houver delegação) |
|---|---|---|
| **Backend / API** | framework async, service layer (rotas finas), contrato de erro, teste por rota | — (o fluxo principal costuma bastar) |
| **Frontend** | framework, estado/dados, sem PII em URL/query, estados de loading/erro | — |
| **DB / dados** | separação de schemas, somente-leitura onde exigido, guardrails de query, migrations sob revisão humana | — |
| **Vetorial / RAG** | coleções por intenção, contrato de payload/metadata, filtro obrigatório, coleção escolhida pelo nó (não pelo LLM) | — |
| **IA / agente** | topologia do grafo, onde o LLM decide (escopo fechado), contrato de tool, grounding | `tool-use-evaluator`: valida uso de tools/guardrails na trajetória |
| **Ingestão** | pipeline offline determinístico, contrato de metadata, sem LLM raciocinando | — |
| **Evals (EDD)** | golden dataset versionado fora do backend, métricas, gate de aceite | `eval-runner`: roda a suíte e devolve só o veredito |

## Regras de bolso

- **Uma rule por área, curta.** Se uma invariante forte vale para várias áreas, ela sobe pro
  `CLAUDE.md` (não se repete em cada rule).
- **Agent só com motivo.** Contexto fresco para não poluir o principal (rodar evals, validar
  trajetória, revisar). Não crie agent "porque sim" — começar mínimo.
- **Simples por padrão.** Gere o baseline de um time real (ADRs, EDD, rules, gate), mas o menor que
  cobre os riscos do PRD. Não transforme um projeto pequeno num harness "enterprise".
- **Cada artefato declara, no topo, qual pergunta responde** e quem o consome.