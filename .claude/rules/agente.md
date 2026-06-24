---
# Regras do agente LangGraph + tools — o coração do produto. Carrega ao tocar backend/agent/.
paths:
  - "backend/agent/**"
---

# Agente — LangGraph determinístico + tools

O agente é um **grafo determinístico**, não um ReAct livre. O engenheiro projeta a topologia; o
LLM decide **só dentro de um nó**. Estas regras são invariantes — quebrar uma é bug, não escolha.

## Topologia
- Grafo de topologia **fixa** (ex.: `planejar → perna_quantitativa → enriquecer → relatorio`).
  Sem laço de tool-calling livre comandado pelo LLM. Fan-out (ex.: por KPI fraco) é data-driven.
- O LLM decide **dentro** de um nó (escolher KPIs, redigir relatório); o roteamento entre nós é
  código, não decisão de LLM solta.

## Tools
- **`search` é tool única, parametrizada pela coleção.** O *nó* escolhe a coleção
  (`camada_semantica` / `diagnostico` / `prescricao`); o LLM não fica num laço escolhendo tool.
- **`run_sql` é somente-leitura, com guardrails determinísticos aplicados ANTES do banco**
  (allowlist: só `SELECT`/`WITH`, uma instrução, `LIMIT` garantido) **e reforçados NO banco**
  (papel `agente_ro` + `SET TRANSACTION READ ONLY` + `statement_timeout`). Nada disso depende do
  LLM. **NUNCA** `INSERT/UPDATE/DELETE/DDL` no schema `negocio`.

## Enriquecimento Qdrant
- **Sempre filtrado** por `periodo_referencia` + dimensão + `kpi_alvo`.
- **NUNCA** filtre por `data_ingestao` — `periodo_referencia ≠ data_ingestao`. Confundir os dois
  é o erro clássico; o filtro é pelo período do *negócio*, não pela data em que o doc foi indexado.

## Grounding (regra de ouro do produto)
- **Toda recomendação prescritiva nasce de um hit da coleção `prescricao`, amarrada a uma `fonte`
  rastreável.** Recomendação sem fonte = falha, não resposta. Se não há prescrição com fonte para
  o caso, diga isso — não invente.

## Premissas e best-effort
- Diante de ambiguidade, assuma defaults sensatos (período-alvo = mês atual +1) e **declare as
  premissas no topo do relatório**. Só devolva pergunta quando nada é resolvível.
- Modelos via `app.config.settings` (`llm_model_forte` / `llm_model_rapido`). Não hardcode model id.
