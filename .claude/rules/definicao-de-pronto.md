# Definição de Pronto (DoD) + critérios de aceite

Regra **transversal** (carrega sempre): define o que conta como "entregue e correto conforme o
harness". É o contrato que torna a execução do agente **mensurável** — sem ele, "está bom?" é
inauditável. O `/scorecard` mede o time contra esta definição.

## Toda issue declara critérios de aceite
Critérios **testáveis**, escritos na issue (saída do `/to-issues`). Ex.: "POST /chat responde em
SSE", não "melhorar o chat". O que não é verificável não é critério de aceite.

## Uma issue só está PRONTA quando (todos):
1. **Gate verde** — `/validar` (ruff + mypy + pytest) passa. Não se comita/fecha vermelho.
2. **Rules respeitadas** — nenhum invariante violado (somente-leitura em `negocio`, grafo
   determinístico, Qdrant filtrado por `periodo_referencia`, grounding com fonte, runtime puro).
3. **Revisor aprovou** — `revisor-codigo` com veredito `aprovado` (ou `aprovado com ressalvas`);
   **nenhum bloqueante** em aberto.
4. **Critérios de aceite atendidos** — cada um com evidência (teste que prova, ou demonstração).
5. **ADR registrado** se houve decisão contestável (`docs/adr/`).
6. **Delivery record gravado** em `metrics/entregas.jsonl` (1 linha JSON por issue — schema em
   `metrics/README.md`). É o que alimenta o `/scorecard`.

## Sinais lagging (medidos depois — ficam fora do loop do agente)
- **Change-failure:** issue reaberta, bug aberto contra issue já merjada, ou mudança pedida em
  review humano. Cada um conta contra a entrega; registre, não esconda.
- **Autonomia:** issue merjada sem edição humana = entrega autônoma. A meta é essa taxa subir ao
  longo do tempo (o harness aperta um dente a cada erro).

> Não persiga vaidade (linhas de código, nº de commits). E cuidado com Goodhart: o gate é alvo
> legítimo (testes reais); métrica de humano (review, bug escapado) **não** entra no que o agente
> otimiza.
