"""Harness de avaliação (EDD) — roda FORA do backend (regra do projeto).

Consome o golden (`seed/evals/golden/narrativas.yaml`), roda o agente sobre cada item e
decide pass/fail. A lógica pura (comparadores) é testada offline em backend/tests; o runner
ao vivo precisa dos serviços reais (Postgres, Qdrant, OpenAI).
"""
