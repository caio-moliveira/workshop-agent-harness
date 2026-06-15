# PRD — Bússola (Agente Analítico de Vendas)

> PRD consolidado, sintetizado da sessão de definição. Fontes: `ideia.md` (rascunho de origem),
> `DECISOES.md` (decisões D1–D11), `docs/adr/0001–0003` e o harness em `.claude/`.
> **Status:** pronto para fatiar em features (SDD) e issues. **Data:** 15 de junho de 2026.

---

## Problem Statement

Um gestor comercial olha o dashboard e vê *que* um indicador caiu — o faturamento recuou, a
recompra ficou abaixo da meta — mas o painel não diz *por que* caiu nem *o que fazer* a respeito.
A explicação mora em texto não estruturado (tickets de suporte, NPS aberto, atas, post-mortems de
campanha) que ninguém cruza sistematicamente com os números. O resultado é diagnóstico tardio e
recomendações baseadas em intuição, sem memória institucional do que já deu certo. O gestor quer,
em linguagem natural, perguntar "como melhorar minhas vendas no próximo mês?" e receber um relatório
fundamentado — não outro gráfico para interpretar sozinho.

## Solution

Um assistente **agêntico, em formato de chat**, que costura duas naturezas de dado para produzir
**relatórios de melhoria acionáveis** para o próximo período:

- o **Postgres** (text-to-SQL, somente leitura) responde *o quê* e *quanto* — quais KPIs estão
  abaixo da meta, em qual dimensão (região/produto/canal), comparando tendência recente **e** o
  mesmo período em anos anteriores (sazonalidade);
- o **Qdrant** responde *por quê* (voz do cliente e contexto operacional) e *o que fazer*
  (playbooks e campanhas que já funcionaram), via recuperação semântica **sempre filtrada**.

A cada pergunta o agente resolve o período-alvo, identifica os KPIs fracos, investiga a causa e o
que já se tentou, e devolve um relatório com diagnóstico e **recomendações priorizadas — cada uma
amarrada a uma fonte rastreável** (sem alucinação prescritiva). O usuário lê o relatório no chat,
inspeciona as fontes citadas e faz perguntas de acompanhamento.

## User Stories

**Gestor comercial (usuário primário)**
1. Como gestor comercial, quero perguntar em linguagem natural "como melhorar minhas vendas no próximo mês?", para receber um relatório fundamentado sem montar consultas.
2. Como gestor comercial, quero que o agente resolva sozinho qual é o "próximo mês" (mês atual + 1, tratando a virada de ano), para não precisar especificar datas.
3. Como gestor comercial, quero que o relatório compare o desempenho recente com o mesmo período de anos anteriores, para separar queda real de variação sazonal.
4. Como gestor comercial, quero ver quais KPIs estão abaixo da meta e em qual dimensão (região, produto, canal), para saber onde o problema se concentra.
5. Como gestor comercial, quero recomendações priorizadas, para agir primeiro no que tem mais impacto.
6. Como gestor comercial, quero que cada recomendação cite a fonte que a sustenta, para confiar na sugestão e não agir por intuição.
7. Como gestor comercial, quero que o agente me diga o que já funcionou e o que não funcionou em situações parecidas, para não repetir erro nem reinventar o que deu certo.
8. Como gestor comercial, quero perguntas de acompanhamento no mesmo chat ("e na região Sudeste?"), para aprofundar sem repetir todo o contexto.
9. Como gestor comercial, quero que, quando minha pergunta for vaga, o agente assuma defaults sensatos e **declare as premissas** no topo do relatório, para o fluxo não travar e eu poder corrigir.
10. Como gestor comercial, quero receber a resposta em tempo interativo (com streaming), para não esperar em uma tela parada.

**Analista de negócio**
11. Como analista, quero explorar um KPI específico ("por que a recompra no Sul caiu no último trimestre?"), para validar o diagnóstico do agente.
12. Como analista, quero inspecionar o SQL que o agente executou, para conferir a leitura quantitativa.
13. Como analista, quero abrir as fontes citadas (tickets, NPS, post-mortems), para auditar o porquê e a prescrição.
14. Como analista, quero uma consulta sazonal de prescrição ("o que funcionou em novembros anteriores para aumentar a conversão?"), para reaproveitar o que já deu certo naquela época.
15. Como analista, quero uma leitura comparativa ("compare este mês com o mesmo mês do ano passado"), para quantificar a variação.
16. Como analista, quero que recomendações já feitas em relatórios anteriores não se repitam, para o relatório agregar algo novo.

**Administrador de conteúdo**
17. Como admin de conteúdo, quero subir documentos qualitativos (tickets, NPS, atas, post-mortems), para alimentar o corpus de diagnóstico e prescrição.
18. Como admin de conteúdo, quero que cada documento guarde o **período que ele descreve** (`periodo_referencia`) separado da data de upload, para o filtro sazonal funcionar.
19. Como admin de conteúdo, quero classificar um post-mortem com o `kpi_alvo` e o `resultado` (positivo/nulo/negativo), para o agente contrastar o que funcionou.
20. Como admin de conteúdo, quero gerenciar o corpus (ver, recarregar) por uma tela, para manter a curadoria.

**Carga de dados / operação**
21. Como operador, quero carregar os dados de vendas e as metas/OKRs no Postgres por seed/upload manual, para ter histórico suficiente (2+ anos) para sazonalidade.
22. Como operador, quero indexar as definições de métricas/colunas e exemplos (pergunta→SQL) na `camada_semantica`, para o agente gerar SQL correto.
23. Como operador, quero subir todo o ambiente com `docker compose up`, para reproduzir o sistema inteiro.

**Garantias do sistema (transversais)**
24. Como dono do produto, quero que toda query ao schema de negócio seja somente leitura, para o agente nunca alterar dados reais.
25. Como dono do produto, quero guardrails determinísticos no SQL (usuário read-only, allowlist, `LIMIT`, timeout), para o agente não rodar consultas perigosas ou caras.
26. Como dono do produto, quero que afirmações prescritivas sem fonte sejam tratadas como falha, para garantir grounding.
27. Como dono do produto, quero que cada run registre tools chamadas, SQL executado e fontes recuperadas (Langfuse + schema de harness), para observabilidade e auditoria.
28. Como dono do produto, quero que o enriquecimento seja sempre filtrado por dimensão + tempo + `kpi_alvo`, para o agente não trazer ruído genérico.

**Avaliação (EDD)**
29. Como autor do workshop, quero um golden dataset de `(pergunta → SQL esperado / resposta esperada / fontes esperadas)`, para medir a qualidade do agente objetivamente.
30. Como autor do workshop, quero que as regressões dos evals rodem como gate de aceite a cada entrega, para não regredir silenciosamente.
31. Como autor do workshop, quero medir execution accuracy, faithfulness e answer relevancy, para cobrir corretude do SQL, fidelidade da narrativa e relevância da resposta.

## Implementation Decisions

**Arquitetura e fases**
- **Duas fases com fronteira rígida** (ADR 0002): ingestão (offline, determinística, sem agente/LLM raciocinando) e runtime (serving, onde o agente vive). O embedding na ingestão é vetorização, não "o agente".
- **Stack:** FastAPI (Python 3.13, uv) · LangGraph · Postgres · Qdrant · MinIO · React · nginx · Docker Compose · Langfuse. Frontend entra após o backend estabilizar.

**O agente (runtime)**
- **Grafo LangGraph determinístico** (ADR 0001): arestas fixas `planejar → perna_quantitativa → (por KPI fraco: diagnostico → prescricao) → sintese → relatorio`. O fan-out é data-driven (nº de KPIs fracos); o LLM decide só dentro de nós (traduzir pergunta→KPIs, gerar SQL, escolher dimensão, redigir narrativa). Sem ReAct livre. Reaproveita as tools individuais do `SQLDatabaseToolkit` dentro do grafo próprio.
- **Chat multi-turno:** porta de entrada conversacional = **reescrita contextual da pergunta** ("condense question") → **roteador de intenção** (caso central vs. casos secundários vs. clarificação) → sub-grafo. O **sub-grafo analítico é stateless**; o estado de sessão (sessões, runs, turnos) vive no schema de harness.
- **Ambiguidade:** best-effort com **premissas declaradas** no topo do relatório (default: período = mês atual + 1; escopo = todos os KPIs com meta). Faz **uma** pergunta de volta só quando nem período nem KPI são resolvíveis.
- **Duas tools, naturezas distintas:** `run_sql` (Postgres, somente leitura, com guardrails) e `search(collection, query, filters)` — **tool única parametrizada pela coleção** (`camada_semantica` | `diagnostico` | `prescricao`), com a coleção escolhida pelo nó do grafo, não por um laço do LLM.
- **Janelas temporais:** tendência = últimos **6 meses**; sazonal = mesmo mês-alvo nos **2 anos anteriores**. Parametrizável; defaults cravados.
- **LLM:** default Claude — tier forte (planejamento/síntese), tier rápido (SQL/roteamento), embedding dedicado na ingestão. Arquitetura provider-agnostic (LangChain), modelo trocável.

**Modelo de dados**
- **Postgres, dois mundos logicamente separados:** schema de **negócio** (vendas: pedidos, itens, clientes, produtos, regiões, canais; + **metas/OKRs** por período e dimensão que definem "baixo"/"com margem") — somente leitura para o agente; schema de **harness** (sessões, runs, chamadas de tool, traces, golden datasets) — leitura/escrita.
- **Qdrant, três coleções por intenção e ciclo de vida:** `camada_semantica` (gera SQL correto; consultada antes da query), `diagnostico` (explica o porquê; após o SQL, para KPIs fracos), `prescricao` (o que fazer; filtrada por `kpi_alvo`). Histórico de relatórios anteriores vive em `prescricao`.
- **Payload das coleções de enriquecimento (§8.3):** `tipo`, `subtipo`, `periodo_referencia` (`YYYY-MM`), `ano`, `mes`, `data_ingestao`, `regiao`, `produto`, `canal`, `fonte`; `prescricao` adiciona `kpi_alvo` e `resultado`. **`periodo_referencia` ≠ `data_ingestao`** e o filtro de enriquecimento nunca usa a data de upload.

**Dataset e EDD**
- **Dataset de e-commerce de varejo genérico**, multicanal, multi-região, clientes recorrentes, 2+ anos de histórico com sazonalidade.
- **5–8 narrativas plantadas** (ADR 0003), cada uma um triplo rastreável (padrão quantitativo no Postgres ↔ documentos de diagnóstico ↔ prescrição com `resultado`, incluindo ≥1 par funcionou/não-funcionou). **O golden dataset nasce das narrativas**; o resto é ruído realista com KPIs saudáveis que não disparam enriquecimento.
- **EDD fora do código do backend**, golden dataset versionado (YAML/JSON), runner pytest como gate de aceite.

**API e fluxo (contratos de alto nível)**
- Endpoint de chat recebe pergunta NL + contexto de sessão e devolve relatório (texto + gráficos) com fontes citadas; relatório e gráficos persistidos no MinIO.
- Ingestão expõe operações de upload (→ MinIO) e indexação (→ Qdrant) e carga de vendas/metas (→ Postgres) — sem agente.

## Testing Decisions

**O que é um bom teste aqui:** testa comportamento externo (pergunta → relatório, fonte citada, SQL read-only respeitado), não detalhes de implementação dos nós. Prefira o **seam mais alto** possível; só desça quando precisar isolar um guardrail ou um filtro.

**Seams (do mais alto ao mais baixo):**
1. **HTTP (end-to-end):** `POST /chat` via httpx — pergunta NL entra, relatório + fontes saem. É onde o golden dataset roda ponta-a-ponta.
2. **Grafo (invoke):** invocar o grafo LangGraph diretamente com a pergunta já reescrita → estado final (relatório, fontes, SQL executado). Pipeline sem HTTP; bom para execution accuracy e faithfulness por caso.
3. **Tools:** `run_sql` contra Postgres de teste seedado (assert resultset + guardrails: read-only, allowlist, `LIMIT`, timeout); `search` contra Qdrant de teste seedado (assert que o filtro dimensão+tempo+`kpi_alvo` recupera as fontes certas e exclui o ruído).
4. **Ingestão:** pipeline determinístico (doc → chunk → embed → payload §8.3); assert da metadata e da separação `periodo_referencia` ≠ `data_ingestao`. Sem agente.
5. **EDD (aceite):** `evals/run_evals.py` sobre o golden dataset — **execution accuracy** (determinística: compara resultset do SQL gerado com o esperado), **faithfulness** e **answer relevancy** (LLM-as-judge). É o gate de aceite de feature, rodado sob `/run-evals`, não no hook de cada edição.

**Quais módulos são testados:** tools (`run_sql`, `search`), nós do grafo (em isolamento e via invoke), pipeline de ingestão, e o agente end-to-end pelo golden dataset. O gate rápido (ruff + mypy + pytest) roda a cada edição via hook; os evals rodam sob comando.

**Prior art:** httpx + pytest para a camada HTTP (padrão da skill `fastapi-patterns`); fixtures de Postgres/Qdrant de teste seedados pelas mesmas rotinas de `/seed-data`.

## Out of Scope

- **Frontend** completo na primeira fatia (entra após o backend estabilizar); por ora, foco backend + agente + ingestão + evals.
- Ingestão automática/contínua a partir de ERP/CRM — a carga é por seed/upload manual.
- Multi-tenant / múltiplas empresas.
- Ações com efeito colateral (disparar campanha, alterar preço) — o agente só recomenda.
- Escrita nos dados de negócio — toda interação com o Postgres de vendas é somente leitura.
- Forecasting estatístico formal — usa tendência e sazonalidade observadas, não modelos preditivos.
- BI self-service genérico para qualquer pergunta ad-hoc sobre qualquer tabela.
- MCP de infra para o agente construtor, loop autônomo (Ralph), e os subagentes de review/testes — adiados no harness.

## Further Notes

- O projeto é um **workshop conduzido como projeto de mundo real**: aceite duplo — a arquitetura/evals demonstram o padrão de forma exemplar **e** o resultado é convincente como produto real.
- O log completo de decisões (D1–D11) está em `DECISOES.md`; os porquês contestáveis em `docs/adr/`.
- O harness de construção (`.claude/`) já existe: `CLAUDE.md`, `rules/` (backend, agente, ingestao, evals), `commands/` (`/feature`, `/run-evals`, `/seed-data`), subagente `eval-runner`, e `settings.json` com hook de gate (`scripts/gate.py`) + permissões.
- **Próximos passos sugeridos:** bootstrap do esqueleto + deps; derivar specs (SDD/BDD) por feature; projetar as narrativas plantadas e o golden dataset inicial via `/seed-data`.
- **Publicação:** ainda não há issue tracker nem remote git. Para fatiar este PRD em issues `ready-for-agent`, rode `/setup-matt-pocock-skills` (escolha tracker local ou GitHub) e depois `/to-issues`.
