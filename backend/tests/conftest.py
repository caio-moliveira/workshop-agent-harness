"""Instala o shim do `xxhash` antes da coleção (hosts com Windows Application Control).

langgraph/langsmith importam `xxhash` no load; em máquinas com a DLL bloqueada por WDAC,
qualquer teste que importe o grafo derruba a coleção do pytest. O shim (condicional, só
quando o real falha) vive em `xxhash_compat` e é reutilizado pelo CLI do eval. Ver ADR 0001/0003.
"""

from __future__ import annotations

import xxhash_compat

xxhash_compat.instalar()
