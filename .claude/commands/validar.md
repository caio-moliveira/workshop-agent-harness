---
description: Gate rápido de validação — ruff + mypy + pytest. Rode antes de cada commit.
---

# /validar — gate rápido

Rode o gate de validação do time e **conserte até passar**. Este é o mesmo gate que o hook de
`Stop` aplica automaticamente; rode-o explicitamente antes de commitar uma fatia.

```bash
uv run ruff check --fix backend && uv run mypy backend && uv run pytest -q
```

- Se **ruff** acusar: deixe o autofix resolver o que dá e corrija o resto à mão.
- Se **mypy** acusar: conserte a tipagem; não silencie com `# type: ignore` sem justificar.
- Se **pytest** falhar: conserte o código (não o teste, salvo se o teste estiver errado).

Só considere a tarefa pronta quando o gate sair **verde**. Não comite vermelho.
