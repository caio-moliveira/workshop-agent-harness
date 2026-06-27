# ADR 0001 — Desabilitar o plugin pytest do langsmith

- **Status:** aceito
- **Data:** 2026-06-27
- **Issue:** #34 (esqueleto andante)

## Contexto

O `langsmith` (dependência transitiva do `langchain`/`langgraph`) registra um plugin de
pytest (`langsmith_plugin`) que é importado no startup do pytest. Esse import puxa `xxhash`,
uma extensão C cuja DLL (`_xxhash`) é **bloqueada por Windows Application Control** em algumas
máquinas — o que derruba a **coleção** do pytest com `ImportError: DLL load failed`, antes de
qualquer teste rodar.

## Decisão

Desabilitar o plugin globalmente via `addopts = "-p no:langsmith_plugin"` no
`[tool.pytest.ini_options]` do `pyproject.toml`.

É uma **decisão de projeto**, não só um remendo de uma máquina:

- A observabilidade do projeto é **Langfuse**, não LangSmith (ver `CLAUDE.md`).
- Os testes rodam **offline e sem LLM** (regra `testes.md`) — não há tracing do LangSmith a
  capturar nos testes, então o plugin não agrega nada.

## Consequências

- `uv run pytest` coleta e roda em qualquer máquina, independente da política de App Control.
- Não afeta o runtime: dentro do container Linux a wheel do `xxhash` é outra e funciona; o
  bloqueio é só no Python do host Windows.
- Se um dia adotarmos tracing do LangSmith em testes, reavaliar (provável que não — é Langfuse).
