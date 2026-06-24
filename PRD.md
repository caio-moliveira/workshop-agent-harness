# PRD — Agente Analítico de Vendas

## 1. Contexto e problema

O gestor comercial olha o dashboard e vê *que* um indicador caiu — faturamento, recompra abaixo da meta —, mas o painel não diz *por quê* nem *o que fazer*. A explicação mora em texto não estruturado (tickets de suporte, NPS aberto, atas, post-mortems de campanha) que ninguém cruza com os números de forma sistemática.

O resultado é diagnóstico tardio e recomendação por intuição, sem memória institucional do que já deu certo. O que o gestor quer é perguntar, em linguagem natural, *"como melhorar minhas vendas no próximo mês?"* e receber um relatório fundamentado — não mais um gráfico para interpretar sozinho.

## 2. Visão do produto

Um assistente de chat, agêntico, que cruza duas naturezas de dado para produzir **relatórios de melhoria acionáveis** para o próximo período:

- os **números** (vendas, metas, sazonalidade) respondem *o quê* e *quanto* — quais KPIs estão abaixo da meta e em qual dimensão (região, produto, canal);
- o **texto** (voz do cliente e contexto operacional) responde *por quê* e *o que fazer* — o que já se tentou e o que funcionou ou falhou.

A cada pergunta, o agente identifica os KPIs fracos, investiga a causa, busca o histórico de tentativas e devolve um relatório com diagnóstico e **recomendações priorizadas, cada uma amarrada a uma fonte rastreável**. O usuário lê no chat, inspeciona as fontes citadas e faz perguntas de acompanhamento.

## 3. Personas

**Gestor comercial — primária.** Decide ações para o próximo período. Quer resposta fundamentada sem montar consulta.

**Analista de negócio — secundária.** Valida o diagnóstico, explora um KPI específico, audita as fontes e o raciocínio do agente.

## 4. Objetivos e métricas de sucesso

- O gestor obtém um relatório acionável a partir de uma pergunta em linguagem natural, sem conhecimento técnico.
- Toda recomendação prescritiva vem com fonte rastreável — **zero prescrição sem origem**.
- O diagnóstico separa queda real de variação sazonal.
- A resposta chega em tempo interativo (streaming).
- O agente é mensurável: existe um critério objetivo de "está bom o suficiente" antes de subir o código.

## 5. Requisitos funcionais

**Caso central**

- Perguntar *"como melhorar minhas vendas no próximo mês?"* e receber um relatório fundamentado.
- O agente resolve sozinho o período-alvo (mês atual + 1, tratando a virada de ano) e o escopo quando a pergunta é vaga, **declarando as premissas no topo do relatório**.
- O relatório mostra quais KPIs estão abaixo da meta e em qual dimensão, comparando a tendência recente com o mesmo período de anos anteriores.
- Recomendações priorizadas, cada uma com a fonte que a sustenta.
- O agente diz o que já funcionou e o que não funcionou em situações parecidas.
- Recomendações já feitas em relatórios anteriores não se repetem.

**Conversa**

- Perguntas de acompanhamento no mesmo chat ("e na região Sudeste?"), sem repetir o contexto.
- Resposta com streaming.

**Exploração (analista)**

- Explorar um KPI específico e inspecionar o SQL executado e as fontes citadas.
- Consultas comparativas e sazonais ("o que funcionou em novembros anteriores para aumentar a conversão?").

## 6. Princípios e restrições

**Princípios de produto**

- **Grounding acima de tudo:** afirmação prescritiva sem fonte é falha, não resposta.
- **Somente leitura no negócio:** o agente nunca altera dados reais de vendas.
- **Best-effort com transparência:** diante de ambiguidade, assume defaults sensatos e os declara; só devolve uma pergunta quando nada é resolvível.
- **O agente recomenda, não age:** nenhum efeito colateral (disparar campanha, mudar preço).

**Restrições técnicas (fixas)**

- Backend **FastAPI** (Python). Agentes em **LangChain/LangGraph**. Frontend **React**.
- Base já existente e mantida: **Postgres** (vendas/metas, ~5 anos) e coleções do **Qdrant** (corpus qualitativo já indexado).
- **Sem ingestão neste projeto:** os stores chegam pré-populados; o app apenas consome.

## 7. Premissas

- Os dados já estão carregados e disponíveis (Postgres populado, Qdrant indexado). A estrutura é insumo, não entrega.
- O ambiente sobe completo para demonstração e execução.

## 8. Fora de escopo

- Ingestão ou carga de dados de qualquer tipo.
- Multi-tenant / múltiplas empresas.
- Ações com efeito colateral — o agente só recomenda.
- Escrita nos dados de negócio.
- Forecasting estatístico formal — usa tendência e sazonalidade observadas, não modelos preditivos.
- BI self-service genérico para qualquer pergunta ad-hoc sobre qualquer tabela.

## 9. O que fica para a fase de spec / harness

Decisões deliberadamente fora do PRD, a serem definidas ao montar o harness **antes** da execução:

- Topologia do agente (grafo, nós, roteamento, multi-turno).
- Contrato das tools (acesso ao SQL e à busca semântica) e guardrails determinísticos.
- Janelas temporais de tendência e sazonalidade (parametrizáveis).
- Modelos (LLM e embedding) e a camada provider-agnostic.
- Estratégia de avaliação: golden dataset e o avaliador que decide pass/fail antes do deploy.
- Observabilidade e persistência de relatórios.