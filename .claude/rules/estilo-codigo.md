---
# Estilo de código Python — carrega só quando o agente toca arquivos .py do backend.
paths:
  - "backend/**/*.py"
  - "seed/**/*.py"
---

# Estilo de código (Python)

Padrão de estilo do time. O hook de `PostToolUse` já roda `ruff format` + `ruff check --fix`
a cada edição — escreva código que **passa limpo** sem depender do autofix.

- **Formatação/lint:** `ruff` (config em `pyproject.toml`). `line-length = 100`, alvo `py313`.
- **Tipagem:** `mypy` (`python_version = 3.13`). Toda função pública tem type hints completos.
  Evite `Any`; quando inevitável, comente o porquê. Prefira `X | None` a `Optional[X]`.
- **`from __future__ import annotations`** no topo de cada módulo (anotações como string).
- **Docstrings curtas em PT-BR** explicando o *porquê*, não o *o quê*. Uma linha quando possível.
- **Nomes do domínio em português** (`faturamento`, `taxa_recompra`, `periodo_referencia`,
  `kpi_alvo`). Não traduza o domínio para inglês no meio do código.
- **Sem `print`** em código de runtime — use `logging`. `print` só em scripts de `seed/`.
- **Funções pequenas e puras** onde der; efeito colateral (I/O, rede, DB) isolado e explícito.
- **Sem segredo hardcoded** — tudo via `app.config.settings` (pydantic-settings lê do `.env`).
