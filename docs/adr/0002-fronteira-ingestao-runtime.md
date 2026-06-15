# ADR 0002: Fronteira rígida entre ingestão e runtime

## Contexto
O sistema tem duas fases: ingestão (chunk/embed/index, carga de dados) e runtime (serving, onde o
agente vive). É tentador deixar o agente "ingerir sob demanda".

## Decisão
A ingestão é offline, determinística e **sem agente / sem LLM raciocinando** (o embedding é só
vetorização). O agente existe **apenas** no runtime e nunca participa da ingestão.

## Alternativas consideradas
- **Ingestão agêntica** (o agente decide o que indexar): rejeitada — não-determinística, difícil de
  reproduzir, mistura responsabilidades e dificulta o EDD.

## Consequências
- (+) Ingestão reproduzível e testável isoladamente; runtime mais simples; fronteira de segurança clara.
- (−) Curadoria/normalização do corpus vira responsabilidade explícita da ingestão (documentada).
- Invariante no `CLAUDE.md`; relacionada à §7 do PRD.
