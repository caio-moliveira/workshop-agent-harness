"""Gate de avaliação EDD (Evaluation-Driven Development) do agente.

Mede a QUALIDADE DA RESPOSTA do produto (não a entrega — isso é o /scorecard) contra o
golden dataset (`seed/evals/golden/narrativas.yaml`). Vive fora do runtime da app: roda
explicitamente, com LLM + stores reais. As funções de pontuação são puras e testáveis.
"""

from __future__ import annotations

# Garante o shim do xxhash ANTES de qualquer import do agente (langgraph) no CLI do eval,
# em hosts com a DLL bloqueada por WDAC (ADR 0003). No container Linux é no-op.
import xxhash_compat

xxhash_compat.instalar()
