# Banco de entrevista — por cluster

Sete clusters. Para cada um: o **objetivo**, **o que inferir do PRD** (não pergunte isso), as
**perguntas de lacuna** (só faça as que o PRD não respondeu) e o **artefato** que as respostas
alimentam. Conduza um cluster por vez, em lotes de 2–3 perguntas.

---

## A. Alinhamento e invariantes → `CLAUDE.md` (raiz) · pilar: estado/memória

**Objetivo:** capturar o que vale para o projeto inteiro e nunca deve ser violado.

**Inferir do PRD:** a stack, os comandos de build/test/run, a separação de fases, restrições
fortes ("somente leitura", "não escreve no schema de negócio"), critérios de sucesso.

**Perguntas de lacuna:**
- Quais são as três a cinco regras que o agente *nunca* pode quebrar, mesmo que pareça útil?
- Quais comandos definem "rodar o projeto" e "validar o projeto"?
- Há convenções de código não óbvias (estilo, naming, libs proibidas) que devem estar sempre em
  contexto?

**Artefato:** índice enxuto de invariantes + comandos no `CLAUDE.md` raiz.

---

## B. Perímetro e convenções por área → `rules/` · pilar: estado/memória

**Objetivo:** regras que só valem em certos diretórios, carregadas pelo escopo.

**Inferir do PRD:** as áreas do projeto (backend, frontend, harness, ingestão), e os padrões que
cada uma já implica (ex.: "toda tool segue um contrato base").

**Perguntas de lacuna:**
- Quando o agente edita o backend, o que ele sempre precisa lembrar que não se aplica ao frontend
  (e vice-versa)?
- Existem caminhos/arquivos sensíveis que o agente não deve tocar sem revisão (migrations,
  configs de infra)?
- Há um padrão obrigatório para criar um novo componente daquele tipo (rota, tool, feature)?

**Artefato:** um arquivo por área em `rules/` (regras path-scoped, curtas).

---

## C. Validação e o ciclo do erro → `settings.json` (hooks) + `evals/` · pilar: validação

**Objetivo:** definir o que é "pronto" e o que roda automaticamente. É o pilar que mais protege.

**Inferir do PRD:** a estratégia de avaliação (EDD), as métricas de qualidade, o "definition of
done".

**Perguntas de lacuna:**
- O que precisa rodar e passar a cada edição de código, sem exceção (lint, types, testes, evals)?
- Quando uma falha acontece, ela deve virar um teste? uma regra no CLAUDE.md? um hook? Quem decide?
- Há checagens que devem *bloquear* uma ação (gate hard) versus apenas avisar?
- O aceite de uma feature depende de eval passar? Qual o dataset/critério?

**Artefato:** bloco `hooks` no `settings.json` (PostToolUse rodando os gates) + estrutura `evals/`.

---

## D. Ferramentas e infra → `.mcp.json` + `skills/` · pilar: ferramentas

**Objetivo:** dar ao agente as ferramentas certas e encapsular operações repetíveis.

**Inferir do PRD:** os stores e serviços (Postgres, Qdrant, MinIO), e as operações que se repetem
(criar uma tool, uma rota, um eval, uma feature).

**Perguntas de lacuna:**
- O agente precisa inspecionar a infra real enquanto constrói (ver o schema vivo do Postgres,
  conferir uma coleção do Qdrant)? Se sim, quais.
- Quais operações você se vê repetindo o suficiente para virar uma skill própria do projeto?
- Há ferramentas externas (CI, issue tracker) que o agente deveria alcançar?

**Artefato:** servidores em `.mcp.json` + pastas em `skills/` para as operações repetíveis.

---

## E. Memória e continuidade → `CLAUDE.md` · `docs/adr/` · `HANDOFF.md` · pilar: estado/memória

**Objetivo:** garantir que o conhecimento durável sobreviva ao reset de contexto.

**Inferir do PRD:** as decisões de arquitetura já tomadas (que viram ADRs) e as questões em aberto.

**Perguntas de lacuna:**
- Quando uma decisão importante for tomada, onde ela deve ficar registrada para o próximo agente
  entender o *porquê*, não só o resultado?
- Sessões longas precisam de handoff (resumo de objetivo, feito, próximos passos) para outro
  agente continuar?
- Há aprendizados recorrentes que o agente deveria anotar para si entre sessões?

**Artefato:** ADRs em `docs/adr/`, template `HANDOFF.md`, e a nota sobre `MEMORY.md` (nível usuário).

---

## F. Orquestração e fluxo → `commands/` + `agents/` · pilar: execução

**Objetivo:** capturar os workflows repetidos e a delegação — sem complicar cedo demais.

**Inferir do PRD:** o tipo de trabalho (greenfield → começa com um fluxo de POC/Projeto; depois
features → Feature Flow).

**Perguntas de lacuna:**
- Quais sequências de passos você repete o bastante para virar um comando (`/feature`, `/poc`,
  `/run-evals`)?
- Há tarefas que merecem um subagente de contexto fresco (rodar evals, revisar, escrever testes)
  para não poluir o contexto principal?
- Você quer um loop autônomo (Ralph) para certas tarefas, ou prefere manter o humano no passo?

**Artefato:** comandos em `commands/`, subagentes em `agents/`. Recomende o mínimo; só adicione
subagente/loop quando houver repetição ou tamanho que justifique.

---

## G. Permissões e autonomia → `settings.json` (permissions) · pilar: execução

**Objetivo:** definir o perímetro do que o agente faz sozinho versus o que pede aprovação.

**Inferir do PRD:** restrições de segurança (somente leitura no banco de negócio) e ações
sensíveis.

**Perguntas de lacuna:**
- Quais comandos/ferramentas o agente pode executar sem pedir permissão?
- Quais ações exigem aprovação explícita (migrations, escrita em stores, comandos destrutivos)?
- Há diretórios ou operações que devem ser sempre negados?

**Artefato:** bloco `permissions` (`allow`/`deny`) no `settings.json`.