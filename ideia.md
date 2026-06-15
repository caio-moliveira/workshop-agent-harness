Agente Analítico de Vendas

> **Codinome provisório:** Bússola
> **Versão:** 0.1 (rascunho)
> **Data:** 15 de junho de 2026
> **Autor:** Caio
> **Status:** Em definição — base para o SPEC (Spec-Driven Development)

---

## 1. Sumário executivo

O **Agente Analítico de Vendas** é um assistente agêntico que combina *text-to-SQL* sobre os dados transacionais de vendas (Postgres) com recuperação de conhecimento qualitativo (Qdrant) para produzir **relatórios acionáveis** sobre como melhorar indicadores comerciais no próximo período.

A diferença em relação a um dashboard ou a um text-to-SQL convencional é a costura de duas naturezas de dado: o Postgres responde *o quê* e *quanto* (o faturamento caiu, a recompra está abaixo da meta), e o Qdrant responde *por quê* (a voz do cliente, o contexto operacional) e *o que fazer* (playbooks e campanhas que já funcionaram). O agente decide, a cada pergunta, quais indicadores investigar e quais fontes cruzar, e fundamenta cada recomendação em evidência rastreável.

Este documento define o produto. A implementação será conduzida via Spec-Driven Development (o PRD alimenta um SPEC) e o aceite de cada entrega será controlado por Eval-Driven Development (EDD).

---

## 2. Contexto e problema

Times comerciais já têm dashboards que mostram *que* um indicador caiu, mas não *por que* caiu nem *o que fazer* a respeito. A explicação costuma morar em texto não estruturado — tickets de suporte, NPS aberto, atas, post-mortems de campanha — que ninguém cruza sistematicamente com os números. O resultado é diagnóstico tardio e recomendações baseadas em intuição, sem memória institucional do que já deu certo.

O problema central que este produto resolve: **transformar dados de vendas e conhecimento qualitativo disperso em um relatório de melhoria fundamentado, sob demanda, para o próximo período.**

---

## 3. Objetivos e não-objetivos

### 3.1 Objetivos

- Permitir que um usuário de negócio pergunte, em linguagem natural, como melhorar suas vendas (ou um KPI específico) no próximo período e receba um relatório fundamentado.
- Cruzar automaticamente a leitura quantitativa (Postgres) com a explicação e a prescrição qualitativas (Qdrant).
- Aproveitar a sazonalidade: comparar não só os meses recentes, mas o mesmo período de anos anteriores.
- Garantir que toda recomendação seja rastreável a uma fonte (sem alucinação prescritiva).
- Servir como projeto de referência arquitetural reaproveitável, com boas práticas de estrutura de repositório e avaliação.

### 3.2 Não-objetivos (nesta versão)

- Não é uma ferramenta de BI self-service genérica para qualquer pergunta ad-hoc sobre qualquer tabela.
- Não executa ações no mundo real (não dispara campanhas, não altera preços) — apenas recomenda.
- Não escreve nos dados de negócio; toda a interação com o Postgres de vendas é somente leitura.
- Não cobre previsão estatística formal (forecasting) — usa tendência e sazonalidade observadas, não modelos preditivos.

---

## 4. Personas e usuários

- **Gestor comercial / de vendas** — usuário primário. Quer entender o desempenho recente e receber recomendações priorizadas para o próximo mês.
- **Analista de negócio** — explora indicadores específicos, valida o diagnóstico do agente, consulta as fontes citadas.
- **Administrador de conteúdo** — responsável por subir e curar os documentos que alimentam o Qdrant (campanhas, exports de tickets, NPS).

---

## 5. Casos de uso

### 5.1 Caso central

> "Como faço para melhorar minhas vendas no próximo mês?"

O agente resolve o período-alvo, identifica os KPIs abaixo da meta ou com margem, investiga o porquê e o que já funcionou, e devolve um relatório com diagnóstico e recomendações priorizadas.

### 5.2 Casos secundários

- "Por que a recompra na região Sul caiu no último trimestre?" — diagnóstico focado em um KPI/dimensão.
- "O que funcionou em novembros anteriores para aumentar a conversão?" — consulta sazonal de prescrição.
- "Compare o desempenho deste mês com o mesmo mês do ano passado." — leitura quantitativa comparativa.

---

## 6. Escopo

### 6.1 No escopo (MVP)

- Ingestão de documentos qualitativos (upload → MinIO → chunk/embed → Qdrant).
- Carga dos dados de vendas e metas no Postgres.
- Agente de runtime com text-to-SQL (somente leitura) e enriquecimento por recuperação filtrada.
- Geração de relatório textual com gráficos, persistido no MinIO.
- Frontend para fazer perguntas, visualizar o relatório e inspecionar as fontes citadas.
- Suíte de avaliação (EDD).

### 6.2 Fora do escopo (futuro)

- Ingestão automática/contínua a partir de sistemas-fonte (ERP/CRM) — na primeira versão, a carga é feita por seed/upload manual.
- Multi-tenant / múltiplas empresas.
- Ações com efeito colateral (disparo de campanha, alteração de preço).
- Forecasting estatístico.

---

## 7. Visão de arquitetura

O sistema opera em **duas fases distintas**, e essa separação é um princípio de projeto: o agente vive apenas no runtime e nunca participa da ingestão.

### 7.1 Fase de ingestão (offline, determinística, sem agente)

- Documentos qualitativos sobem para o **MinIO** (armazenamento do bruto).
- Um pipeline faz *chunking* + *embedding* com a metadata combinada e indexa no **Qdrant** (coleções `diagnostico` e `prescricao`).
- Em paralelo, os **dados de vendas e metas/OKRs** são carregados no **Postgres**, e as **definições de métricas/schema** são indexadas na coleção `camada_semantica` do Qdrant.
- Observação: o *embedding* usa um modelo, mas não é "o agente" — é vetorização, sem raciocínio nem tools.

### 7.2 Fase de runtime (serving, onde o agente vive)

- O **Frontend (React)** envia a pergunta; a requisição passa pelo **nginx** (reverse proxy) e chega ao **FastAPI** (camada HTTP).
- Dentro do serving, o **Agente (LangGraph)** orquestra as tools: lê do Postgres (via SQL) e do Qdrant (semântica + enriquecimento) e grava o relatório no MinIO.
- A resposta retorna pela mesma cadeia até o frontend.

### 7.3 Stack

Backend FastAPI (Python); frontend React; orquestração do agente em LangGraph (reaproveitando as tools individuais do `SQLDatabaseToolkit` do LangChain dentro do grafo próprio, sem usar o agente pronto); Postgres, Qdrant e MinIO como stores; nginx como reverse proxy; tudo orquestrado por Docker Compose. Observabilidade de execução via Langfuse (ou equivalente).

---

## 8. Modelo de dados

### 8.1 Postgres

Dois "mundos" logicamente separados no mesmo banco:

- **Schema de negócio (somente leitura para o agente):** tabelas de vendas (pedidos, itens, clientes, produtos, regiões, canais) e uma tabela de **metas/OKRs** por período e dimensão, que define o que é "baixo" ou "com margem".
- **Schema do harness (leitura/escrita):** sessões, runs, chamadas de tool, traces e os golden datasets de avaliação.

### 8.2 Qdrant — três coleções

As coleções são separadas por **intenção de busca e ciclo de vida**, não por elegância de taxonomia.

| Coleção | Conteúdo | Papel | Quando é consultada |
|---|---|---|---|
| `camada_semantica` | Definições de métricas, descrições de tabelas/colunas, exemplos `(pergunta → SQL)`, valores canônicos | Ajuda a gerar o SQL correto | Antes da query (perna quantitativa) |
| `diagnostico` | Voz do cliente e contexto operacional (tickets, NPS aberto, reclamações, atas, mudanças de preço/promoções) | Explica o porquê | Após o SQL, para os KPIs fracos |
| `prescricao` | Playbooks, post-mortems de campanhas com resultados, boas práticas, benchmarks, relatórios anteriores | Orienta o que fazer | Após o diagnóstico, filtrada por KPI |

As metas/OKRs ficam no Postgres (são números, devem ser queryáveis). O histórico de relatórios anteriores vive dentro de `prescricao`, para dar continuidade e evitar repetição de recomendações.

### 8.3 Payload (metadata) das coleções de enriquecimento

Toda coleção de enriquecimento espelha as dimensões do Postgres, mais campos temporais. Campos comuns a `diagnostico` e `prescricao`:

- `tipo`, `subtipo`
- `periodo_referencia` (formato `YYYY-MM`, o período que o conteúdo descreve — **não** a data de upload)
- `ano` (inteiro) e `mes` (inteiro) separados, para permitir filtro sazonal por mês cruzando anos
- `data_ingestao` (separada e nunca usada para filtrar enriquecimento)
- `regiao`, `produto`, `canal`
- `fonte` (URI do documento bruto no MinIO)

Campos adicionais específicos de `prescricao`:

- `kpi_alvo` — qual indicador a estratégia mirava (essencial para a busca filtrada)
- `resultado` — o efeito observado (positivo/nulo/negativo), base para o "deu certo / não deu"

---

## 9. Fluxo do agente (retriever)

1. **Pergunta do usuário.** Entrada em linguagem natural.
2. **Planejamento.** O agente resolve o tempo (próximo mês = mês atual + 1, tratando a virada de ano), monta as duas janelas (tendência: últimos N meses; sazonal: o mesmo mês-alvo em anos anteriores) e traduz o pedido vago em KPIs concretos consultando a `camada_semantica` e as metas.
3. **Perna quantitativa (`run_sql` → Postgres).** Consulta as duas janelas e cruza com as metas para identificar os KPIs abaixo da meta ou com margem e a dimensão (região/produto/canal) onde o problema se concentra.
4. **Roteamento.** Para cada KPI fraco, abre uma investigação. KPIs saudáveis não disparam enriquecimento.
5. **Enriquecimento — diagnóstico (`search` → Qdrant `diagnostico`).** Busca semântica **filtrada** por `mes` (sazonal) + período recente + dimensão, para entender o porquê.
6. **Enriquecimento — prescrição (`search` → Qdrant `prescricao`).** Busca filtrada por `kpi_alvo` + `mes`, para encontrar o que já se tentou para mover aquele indicador naquela época. Os passos 5–6 repetem por KPI fraco.
7. **Síntese e grounding.** Contrasta o que funcionou (com base no campo `resultado`) e o que não funcionou, cruza com os bloqueios do diagnóstico, e monta recomendações priorizadas — cada uma amarrada a sua fonte.
8. **Relatório (resposta).** Gera texto + gráficos, persiste no MinIO e registra o run no schema de harness do Postgres.

---

## 10. Requisitos funcionais

**Ingestão**
- RF-01: O sistema deve permitir upload de documentos e armazená-los em bruto no MinIO.
- RF-02: O sistema deve fazer chunking e embedding dos documentos e indexá-los no Qdrant com a metadata definida na seção 8.3.
- RF-03: O sistema deve permitir carregar dados de vendas e metas no Postgres e indexar as definições de métricas na `camada_semantica`.

**Text-to-SQL**
- RF-04: O agente deve recuperar contexto semântico relevante (tabelas, colunas, métricas, exemplos) antes de gerar SQL.
- RF-05: O agente deve gerar, validar e executar SQL somente leitura sobre o schema de negócio.
- RF-06: O agente deve comparar realizado contra meta e identificar KPIs fracos e suas dimensões.

**Retriever / enriquecimento**
- RF-07: O agente deve, para cada KPI fraco, executar busca filtrada na `diagnostico` (por mês sazonal, período recente e dimensão).
- RF-08: O agente deve executar busca filtrada na `prescricao` por `kpi_alvo` e `mes`.
- RF-09: O agente deve recuperar relatórios anteriores para evitar recomendações repetidas.

**Relatório**
- RF-10: O agente deve gerar um relatório com estado atual (números, tendência, sazonalidade), diagnóstico, o que funcionou/não funcionou e recomendações priorizadas.
- RF-11: Cada recomendação deve citar a fonte que a sustenta.
- RF-12: O relatório e os gráficos devem ser persistidos no MinIO e disponibilizados ao usuário.

**Frontend**
- RF-13: O usuário deve poder enviar perguntas em linguagem natural.
- RF-14: O usuário deve poder visualizar o relatório e inspecionar as fontes citadas.
- RF-15: O administrador deve poder subir e gerenciar os documentos do corpus.

---

## 11. Requisitos não-funcionais

- RNF-01 (Segurança do SQL): toda execução usa usuário de banco somente leitura, com parser/allowlist de tabelas, `LIMIT` forçado e timeout. O *query-checker* via LLM é uma camada adicional (soft), não substituta dos guardrails determinísticos (hard).
- RNF-02 (Grounding): o agente não deve produzir recomendações sem fonte; afirmações prescritivas sem suporte são tratadas como falha.
- RNF-03 (Privacidade): dados pessoais não devem ir para parâmetros de URL; o corpus pode conter PII e deve ser tratado conforme política de dados.
- RNF-04 (Observabilidade): cada run deve registrar tools chamadas, SQL executado e fontes recuperadas (Langfuse + schema de harness).
- RNF-05 (Reprodutibilidade): o ambiente completo deve subir via `docker compose up`.
- RNF-06 (Performance): geração de um relatório padrão deve responder em tempo aceitável para uso interativo (meta a calibrar; ver questões em aberto).

---

## 12. Métricas de sucesso

**Produto**
- Tempo para obter um diagnóstico fundamentado (vs. processo manual atual).
- Proporção de recomendações consideradas úteis/acionáveis pelos usuários.
- Adoção: perguntas/relatórios por usuário ativo por semana.

**Qualidade técnica (EDD)**
- *Execution accuracy*: o SQL gerado roda e bate o resultado esperado.
- *Faithfulness*: a narrativa não afirma nada além do que os números e as fontes sustentam.
- *Answer relevancy*: a resposta endereça o que foi perguntado.

---

## 13. Estratégia de avaliação (EDD)

A avaliação é cidadã de primeira classe e fica fora do código do backend. Um golden dataset de `(pergunta → SQL esperado / resposta esperada / fontes esperadas)` permite medir as métricas da seção 12. As regressões devem rodar como gate de aceite a cada entrega (alinhado ao Eval-Driven Development).

---

## 14. Riscos e mitigações

- **SQL incorreto em schemas grandes** → recuperação semântica de tabelas/colunas e few-shot examples na `camada_semantica`; guardrails de execução.
- **Enriquecimento genérico (ruído)** → busca sempre filtrada por dimensão + tempo + `kpi_alvo`; coleções separadas por intenção.
- **Alucinação prescritiva** → exigência de grounding (RNF-02) e medição de faithfulness.
- **Confusão entre data de referência e data de ingestão** → metadata `periodo_referencia` separada de `data_ingestao`; filtro de enriquecimento nunca usa a data de upload.
- **Corpus pobre ou desatualizado** → curadoria do conteúdo de prescrição (campanhas com `resultado`); processo de ingestão documentado.

---

## 15. Premissas e questões em aberto

- **Premissa:** os dados de vendas no Postgres serão um dataset (sintético ou real) com histórico suficiente para sazonalidade (idealmente 2+ anos).
- **Em aberto:** o dataset de negócio será sintético genérico (e-commerce/varejo) ou espelhará um domínio específico?
- **Em aberto:** tamanho das janelas (N meses de tendência; quantos anos de sazonalidade)?
- **Em aberto:** o enriquecimento usa uma tool de busca por coleção ou uma tool única parametrizada pela coleção?
- **Em aberto:** metas de performance (latência aceitável por relatório) a calibrar.

---

## 16. Próximos passos

1. Fechar as questões da seção 15.
2. Derivar o **SPEC** (SDD) a partir deste PRD, com especificações por feature em BDD/Gherkin.
3. Definir o schema concreto do Postgres (vendas + metas) e o payload final de cada coleção do Qdrant.
4. Montar o golden dataset inicial de avaliação (EDD).
5. (Posterior) Estruturar o harness de construção (CLAUDE.md, skills, hooks, commands) para conduzir a implementação via agente de código.