# ADR 0003 — Shim condicional do xxhash para o gate em hosts com Windows App Control

- **Status:** aceito
- **Data:** 2026-06-27
- **Issue:** #36 (grafo + /chat SSE)

## Contexto

`langgraph`/`langsmith`/`langchain_core` importam `xxhash` no carregamento
(`xxh3_128`, `xxh3_128_hexdigest`). Em algumas máquinas Windows, a DLL `_xxhash` é
**bloqueada por Windows Application Control (WDAC)** — `ImportError: DLL load failed`. Isso
derruba a **coleção** do pytest no host (qualquer teste que importe o grafo) e impede rodar o
gate `/validar`.

## Decisão

Um `backend/tests/conftest.py` instala um **shim mínimo** de `xxhash` em `sys.modules`,
**condicional** (só quando o import real falha), com `blake2b(digest_size=16)` cobrindo os dois
símbolos usados (`xxh3_128(...).digest()` e `xxh3_128_hexdigest(...)`).

## Consequências

- O gate roda no host afetado; em máquinas com a DLL liberada, o shim **não entra** (usa o real).
- **Não afeta a produção:** dentro do container Linux a wheel real do `xxhash` funciona; o shim
  é só de teste (conftest).
- O valor do hash é irrelevante nos testes (tracing do langsmith desligado, LLM mockado).
- Correção definitiva = TI liberar a DLL `_xxhash` no WDAC. Até lá, o shim destrava o gate.
- Relacionado ao ADR 0001 (desabilitação do plugin pytest do langsmith, mesma causa raiz).
