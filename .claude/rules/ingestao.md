---
description: Regras ao editar a ingestão (pipeline offline, sem agente). Aplica a ingestion/**.
---
# Ingestão (offline, determinística)

- **Sem agente, sem raciocínio de LLM.** O fluxo é determinístico:
  upload→MinIO → chunk → embed → index no Qdrant. O embedding é vetorização, não "o agente".
- Metadata segue o contrato da **§8.3** do PRD: `tipo`, `subtipo`,
  `periodo_referencia` (`YYYY-MM`), `ano` (int), `mes` (int), `data_ingestao`,
  `regiao`, `produto`, `canal`, `fonte`. `prescricao` adiciona `kpi_alvo` e `resultado`.
- **`periodo_referencia` ≠ `data_ingestao`.** O período é o que o conteúdo descreve;
  `data_ingestao` é só auditoria e **nunca** filtra enriquecimento.
- Três coleções por intenção: `camada_semantica`, `diagnostico`, `prescricao`. Não misture conteúdos.
- Carga de vendas/metas no Postgres e indexação das definições de métricas na `camada_semantica`
  fazem parte da ingestão, **não** do runtime.
