"""Shim condicional do `xxhash` para hosts com Windows Application Control (ADR 0003).

A DLL `_xxhash` é bloqueada por política (WDAC) em algumas máquinas; langgraph/langsmith
importam `xxhash` no load (`xxh3_128` / `xxh3_128_hexdigest`), o que impede importar o
agente no host (testes E o CLI do eval). `instalar()` só age quando o xxhash real falha,
com um shim mínimo via blake2b. Na produção (container Linux) a wheel real é usada e isto
não entra — o valor do hash é irrelevante (tracing do langsmith desligado).
"""

from __future__ import annotations

import sys


def instalar() -> None:
    """Instala o shim em sys.modules SE o xxhash real não puder ser importado."""
    try:
        import xxhash  # noqa: F401  -- DLL real disponível, nada a fazer

        return
    except ImportError:
        pass

    import hashlib
    import types
    from typing import Any

    def _digest16(data: Any = b"") -> bytes:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.blake2b(bytes(data) if data else b"", digest_size=16).digest()

    class _Hasher:
        def __init__(self, data: Any = b"") -> None:
            self._d = _digest16(data)

        def digest(self) -> bytes:
            return self._d

        def hexdigest(self) -> str:
            return self._d.hex()

        def intdigest(self) -> int:
            return int.from_bytes(self._d, "big")

    shim = types.ModuleType("xxhash")
    shim.xxh3_128 = lambda data=b"": _Hasher(data)  # type: ignore[attr-defined]
    shim.xxh3_128_hexdigest = lambda data=b"": _digest16(data).hex()  # type: ignore[attr-defined]
    sys.modules["xxhash"] = shim
