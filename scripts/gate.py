"""Gate rápido de validação.

Responde: "a edição que acabei de fazer mantém o projeto válido?"
Roda no hook PostToolUse (settings.json) e via `uv run python scripts/gate.py`.

Roda ruff (lint+format), mypy (types) e pytest (unit) de forma TOLERANTE ao bootstrap:
ferramenta ausente ou diretório de fontes inexistente é PULADO (não falha). "Nenhum teste
coletado" (pytest exit 5) conta como sucesso. Qualquer falha real retorna != 0 e bloqueia.

Os evals (EDD) NÃO rodam aqui — são lentos/custosos e ficam sob `/run-evals`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

# Saída UTF-8 mesmo em consoles legados (Windows cp1252) — senão os símbolos (→ • ✗) quebram o gate.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

SOURCE_DIRS = ["backend", "ingestion", "evals", "seed"]


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def run(cmd: list[str], ok_codes: tuple[int, ...] = (0,)) -> bool:
    print(f"→ {' '.join(cmd)}")
    code = subprocess.run(cmd).returncode
    if code in ok_codes:
        return True
    print(f"  ✗ falhou (exit {code})")
    return False


def existing(dirs: list[str]) -> list[str]:
    return [d for d in dirs if os.path.isdir(d)]


def main() -> int:
    failures = 0

    if have("ruff"):
        failures += not run(["ruff", "check", "--fix", "."])
        failures += not run(["ruff", "format", "."])
    else:
        print("• ruff ausente — pulado (rode `uv sync`)")

    dirs = existing(SOURCE_DIRS)
    if have("mypy") and dirs:
        failures += not run(["mypy", *dirs])
    else:
        print("• mypy / sem fontes — pulado")

    if have("pytest"):
        # exit 5 = nenhum teste coletado → ok no bootstrap
        failures += not run(["pytest", "-q"], ok_codes=(0, 5))
    else:
        print("• pytest ausente — pulado")

    if failures:
        print(f"\nGate VERMELHO ({failures} verificação(ões) falharam).")
        return 1
    print("\nGate VERDE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
