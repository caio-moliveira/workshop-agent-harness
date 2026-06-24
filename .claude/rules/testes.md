---
# Padrão de testes. Carrega ao tocar a suíte.
paths:
  - "backend/tests/**"
---

# Testes — pytest

A suíte é o gate. O hook de `Stop` roda `pytest -q` e **bloqueia** o fim do trabalho se algo
falhar — então o teste tem que ser real e verde, não decorativo.

- **`pytest` + `pytest-asyncio`** (`asyncio_mode = auto`). Testes async são `async def` direto.
- **Nome:** arquivos `test_*.py`, funções `test_*`. Um arquivo por unidade testada.
- **NUNCA comite teste comentado, `@pytest.mark.skip` sem motivo escrito, ou `assert True`.** Um
  teste desligado em silêncio é pior que nenhum — passa no gate sem proteger nada. Se precisa pular,
  escreva o porquê e abra issue.
- **Teste os guardrails determinísticos** com força: `run_sql` rejeita `INSERT/UPDATE/DELETE/DDL`,
  exige instrução única, injeta `LIMIT`; `search` sempre filtra por `periodo_referencia` (nunca
  `data_ingestao`). Esses são os invariantes — cubra-os.
- **NÃO chame o LLM nem APIs externas (OpenAI/Anthropic/Qdrant real) em teste.** Faça mock/fake do
  modelo e dos clientes. Teste deve rodar offline, determinístico e rápido.
- **Banco em teste:** use o fixture/conexão de teste (ex.: SQLite async), não o Postgres de produção.
- **Cada bug corrigido vira um teste de regressão.** O erro não pode voltar.
