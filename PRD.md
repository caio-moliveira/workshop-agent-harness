# PRD — Agente Analítico de Vendas

## Problem Statement

Um gestor comercial olha o dashboard e vê *que* um indicador caiu — o faturamento recuou, a
recompra ficou abaixo da meta — mas o painel não diz *por que* caiu nem *o que fazer* a respeito.
A explicação mora em texto não estruturado (tickets de suporte, NPS aberto, atas, post-mortems de
campanha) que ninguém cruza sistematicamente com os números. O resultado é diagnóstico tardio e
recomendações baseadas em intuição, sem memória institucional do que já deu certo. O gestor quer,
em linguagem natural, perguntar "como melhorar minhas vendas no próximo mês?" e receber um relatório
fundamentado — não outro gráfico para interpretar sozinho.

## Solution

> **Os dados já estão postos e carregados — não há ingestão neste projeto.** ~5 anos de vendas/metas
> vivem no Postgres (schema `negocio`), cuja DDL está em `schema.sql`. O corpus qualitativo
> (tickets, NPS, atas, post-mortems), originado da pasta `seed/corpus/`, **já foi indexado** nas três
> coleções do Qdrant, junto das definições/exemplos da camada semântica. O escopo deste PRD é a
> **aplicação que consome esses dados**. A estrutura dos dados já carregados está documentada na
> seção *Estrutura dos dados (referência)* — para o app entender o que está lá, **não para reproduzir
> a carga**.

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

**Operação / ambiente**
17. Como operador, quero subir todo o ambiente com `docker compose up` (Postgres, Qdrant, MinIO, backend, frontend, nginx, Langfuse) com os stores **já populados**, para reproduzir o sistema inteiro em execução sem rodar nenhuma carga.

**Garantias do sistema (transversais)**
18. Como dono do produto, quero que toda query ao schema de negócio seja somente leitura, para o agente nunca alterar dados reais.
19. Como dono do produto, quero guardrails determinísticos no SQL (usuário read-only, allowlist, `LIMIT`, timeout), para o agente não rodar consultas perigosas ou caras.
20. Como dono do produto, quero que afirmações prescritivas sem fonte sejam tratadas como falha, para garantir grounding.
21. Como dono do produto, quero que cada run registre tools chamadas, SQL executado e fontes recuperadas (Langfuse + schema de harness), para observabilidade e auditoria.
22. Como dono do produto, quero que o enriquecimento seja sempre filtrado por dimensão + tempo + `kpi_alvo`, para o agente não trazer ruído genérico.

**Avaliação (agente harness, pré-deploy)**
23. Como autor do workshop, quero um golden dataset de `(pergunta → tools esperadas → SQL esperado → fontes esperadas → recomendação esperada)`, para medir a qualidade do agente objetivamente.
24. Como autor do workshop, quero um **agente avaliador em `.claude/agents`** que rode o código contra o golden dataset e julgue se as tools invocadas e a resposta gerada batem com o esperado, para validar uma entrega **antes de subir o código** — sem precisar de um script de evals separado.
25. Como autor do workshop, quero que esse agente avalie execution accuracy, fidelidade das tools/fontes (faithfulness) e relevância da resposta (answer relevancy), e emita um veredito de aceite (pass/fail por caso + agregado), para não regredir silenciosamente.

## Implementation Decisions

**Arquitetura e fases**
- **App é só runtime (serving).** A ingestão **não faz parte deste projeto**: os dados já estão
  carregados (Postgres populado a partir de `schema.sql`; coleções do Qdrant já indexadas a partir
  de `seed/corpus/` e das queries da camada semântica). O app **consome** stores pré-populados;
  a estrutura desses dados está descrita em *Estrutura dos dados (referência)* apenas como
  apontamento, sem nenhuma rotina de carga.
- **Stack:** Backend **FastAPI** (Python 3.13, uv) + **LangChain/LangGraph** — o agente é um grafo
  determinístico LangGraph sobre o ecossistema LangChain, não um ReAct livre. Frontend **React + Vite**.
  Stores: **Postgres** (negócio + harness), **Qdrant** (3 coleções já populadas), **MinIO**
  (persistência de relatórios e gráficos gerados). **nginx** como reverse proxy protegendo a
  aplicação (única porta exposta ao host). **Docker Compose** sobe tudo com os stores já populados;
  **Langfuse** para observabilidade. Embeddings usados na indexação (já realizada):
  **OpenAI `text-embedding-3-large` (3072d)**, arquitetura provider-agnostic (trocável) — o app
  reusa o mesmo modelo só para embeddar a *query* em runtime.

**O agente (runtime)**
- **Grafo LangGraph determinístico**: arestas fixas `planejar → perna_quantitativa → (por KPI fraco: diagnostico → prescricao) → sintese → relatorio`. O fan-out é data-driven (nº de KPIs fracos); o LLM decide só dentro de nós (traduzir pergunta→KPIs, gerar SQL, escolher dimensão, redigir narrativa). Sem ReAct livre. Reaproveita as tools individuais do `SQLDatabaseToolkit` dentro do grafo próprio.
- **Chat multi-turno:** porta de entrada conversacional = **reescrita contextual da pergunta** ("condense question") → **roteador de intenção** (caso central vs. casos secundários vs. clarificação) → sub-grafo. O **sub-grafo analítico é stateless**; o estado de sessão (sessões, runs, turnos) vive no schema de harness.
- **Ambiguidade:** best-effort com **premissas declaradas** no topo do relatório (default: período = mês atual + 1; escopo = todos os KPIs com meta). Faz **uma** pergunta de volta só quando nem período nem KPI são resolvíveis.
- **Duas tools, naturezas distintas:** `run_sql` (Postgres, somente leitura, com guardrails) e `search(collection, query, filters)` — **tool única parametrizada pela coleção** (`camada_semantica` | `diagnostico` | `prescricao`), com a coleção escolhida pelo nó do grafo, não por um laço do LLM.
- **Janelas temporais:** tendência = últimos **6 meses**; sazonal = mesmo mês-alvo nos **2 anos anteriores**. Parametrizável; defaults cravados.
- **LLM:** default Claude — tier forte (planejamento/síntese), tier rápido (SQL/roteamento), embedding dedicado para a query em runtime. Arquitetura provider-agnostic (LangChain), modelo trocável.

**Estrutura dos dados (referência — já carregados, sem ingestão neste projeto)**
- **Postgres, dois mundos separados.** Schema de **negócio** (somente leitura para o agente),
  populado com ~5 anos — DDL de referência em `schema.sql`: dimensões `regioes`, `canais`,
  `categorias`, `produtos`, `clientes`; fatos `pedidos`, `itens_pedido` e `sessoes_diarias`
  (tráfego — denominador da conversão); e `metas` (OKRs por `ano`/`mes`/`kpi`/dimensão, que definem
  "abaixo da meta"). Schema de **harness** (sessões, runs, chamadas de tool, traces, golden datasets)
  — leitura/escrita pelo app, e leitura pelo agente avaliador.
- **Qdrant, três coleções por intenção e ciclo de vida** (já indexadas a partir de `seed/corpus/`):
  `camada_semantica` (definições de KPI + exemplos pergunta→SQL; consultada antes da query),
  `diagnostico` (explica o porquê; consultada após o SQL, por KPI fraco), `prescricao` (o que fazer;
  filtrada por `kpi_alvo`; guarda também o histórico de relatórios anteriores).
- **Payload das coleções de enriquecimento (referência):** `tipo`, `subtipo`,
  `periodo_referencia` (`YYYY-MM`), `ano`, `mes`, `data_ingestao`, `regiao`, `produto`, `canal`,
  `fonte`; `prescricao` adiciona `kpi_alvo` e `resultado` (positivo/nulo/negativo). Atenção em
  runtime: **`periodo_referencia` ≠ `data_ingestao`** e o filtro de enriquecimento nunca usa a data
  de carga — sempre `periodo_referencia` + dimensão + `kpi_alvo`.

**Dados e avaliação**
- **Dados reais, já persistidos:** ~5 anos de vendas/metas de um e-commerce de varejo (multicanal,
  multi-região, clientes recorrentes, com sazonalidade) no Postgres; corpus qualitativo no Qdrant.
  O app **consome** esses dados — não os produz nem os carrega.
- **Situações rastreáveis:** nos dados, um padrão quantitativo (ex.: recompra caindo numa região)
  liga-se a documentos de `diagnostico` (o porquê) e de `prescricao` com `resultado` (o que já se
  tentou — incluindo casos que funcionaram e que não funcionaram); é o que o agente contrasta.
- **Avaliação:** golden dataset de `(pergunta → tools esperadas → SQL esperado → fontes esperadas →
  recomendação esperada)` derivado dessas situações, versionado fora do backend (YAML/JSON);
  **executado e julgado pelo agente avaliador em `.claude/agents`** (ver *Testing Decisions*), não
  por um script de evals.

**API e fluxo (contratos de alto nível)**
- Endpoint de chat recebe pergunta NL + contexto de sessão e devolve relatório (texto + gráficos)
  com fontes citadas; relatório e gráficos persistidos no MinIO.
- **Sem endpoints de ingestão/carga.** O app não expõe upload de corpus nem seed de vendas/metas —
  os stores chegam pré-populados.

## Testing Decisions

**O que é um bom teste aqui:** testa comportamento externo (pergunta → relatório, fonte citada, SQL read-only respeitado), não detalhes de implementação dos nós. Prefira o **seam mais alto** possível; só desça quando precisar isolar um guardrail ou um filtro.

**Seams (do mais alto ao mais baixo):**
1. **HTTP (end-to-end):** `POST /chat` via httpx — pergunta NL entra, relatório + fontes saem. É onde o golden dataset roda ponta-a-ponta (acionado pelo agente avaliador).
2. **Grafo (invoke):** invocar o grafo LangGraph diretamente com a pergunta já reescrita → estado final (relatório, fontes, SQL executado). Pipeline sem HTTP; bom para execution accuracy e faithfulness por caso.
3. **Tools:** `run_sql` contra Postgres de teste com snapshot read-only (assert resultset + guardrails: read-only, allowlist, `LIMIT`, timeout); `search` contra Qdrant de teste com snapshot (assert que o filtro dimensão+tempo+`kpi_alvo` recupera as fontes certas e exclui o ruído).

**Aceite — agente avaliador em `.claude/agents` (substitui o script de evals):**
- O **agent harness** tem duas partes: (a) o **schema de harness** no Postgres, que grava cada run
  (sessão, run, tools chamadas, SQL executado, fontes recuperadas, relatório final, traces espelhando
  o Langfuse) — o registro observável do *que o agente fez*; e (b) o **agente avaliador**,
  um subagente do Claude Code em `.claude/agents/avaliador-vendas.md`.
- **O que o agente avaliador faz, antes de subir o código:** carrega o golden dataset (YAML/JSON
  versionado fora do backend); para cada caso, **roda o código** invocando o agente (pelo seam de
  grafo `invoke` ou por `POST /chat`); lê o run registrado no schema de harness (+ Langfuse) e julga:
    - **tools invocadas == esperadas** (ex.: `run_sql` e depois `search` nas coleções certas com os
      filtros certos — incluindo `periodo_referencia` + dimensão + `kpi_alvo`, nunca `data_ingestao`);
    - **execution accuracy** (determinística): compara o resultset do SQL gerado com o esperado;
    - **faithfulness/grounding**: toda recomendação prescritiva amarrada a uma fonte recuperada;
      afirmação prescritiva sem fonte = falha;
    - **answer relevancy**: a resposta endereça a pergunta.
- **Saída:** veredito **pass/fail por caso + agregado** e um resumo das regressões. O gate falha se
  qualquer checagem dura quebrar (read-only desrespeitado, fonte ausente, execution accuracy abaixo
  do limiar). É acionado sob comando (manual ou na CI antes do deploy), **não** no hook de cada edição.
- **Por que subagente e não script:** centraliza o julgamento (LLM-as-judge) e a orquestração da
  execução num artefato do Claude Code, reproduzível pelo time como passo de "rodar antes de subir",
  sem manter um runner Python paralelo.

**Quais módulos são testados:** tools (`run_sql`, `search`) e nós do grafo (em isolamento e via invoke) pelo pytest; e o agente end-to-end pelo golden dataset, via o agente avaliador. O gate rápido (ruff + mypy + pytest) roda a cada edição via hook; a avaliação do golden dataset roda sob comando, pelo agente em `.claude/agents`.

**Prior art:** httpx + pytest para a camada HTTP e de tools (padrão da skill `fastapi-patterns`); fixtures de Postgres/Qdrant de teste apontando para snapshots read-only pré-populados (não há rotina de seed no app).

## Out of Scope

- **Ingestão / carga de qualquer tipo** — não há seed nem pipeline de ingestão neste projeto; os stores (Postgres e Qdrant) chegam pré-populados e a estrutura é apenas documentada para referência.
- Ingestão automática/contínua a partir de ERP/CRM e upload de corpus pela aplicação.
- Multi-tenant / múltiplas empresas.
- Ações com efeito colateral (disparar campanha, alterar preço) — o agente só recomenda.
- Escrita nos dados de negócio — toda interação com o Postgres de vendas é somente leitura.
- Forecasting estatístico formal — usa tendência e sazonalidade observadas, não modelos preditivos.
- BI self-service genérico para qualquer pergunta ad-hoc sobre qualquer tabela.