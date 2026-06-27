"""CLI do gate EDD: `uv run python -m evals [--out report.json]`.

Monta as dependências REAIS (OpenAI, Qdrant, papel RO), roda o grafo do agente em cada
caso do golden, pontua e imprime um scorecard. Grava o report completo (por caso) em JSON
para inspeção. NÃO faz parte do gate de testes — roda explicitamente (custa LLM + stores).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import cast

from openai import OpenAI
from qdrant_client import QdrantClient

from agent.deps import Dependencias, executor_run_sql
from agent.grafo import construir_grafo
from agent.llm import criar_llm
from agent.tools.embeddings import criar_embedder
from agent.tools.search import ClienteQdrant
from app.config import get_settings
from app.db import criar_engine
from evals.golden import carregar_golden
from evals.judge import JuizOpenAI
from evals.runner import RelatorioEval, rodar_eval


def _montar_grafo_e_juiz() -> tuple[object, JuizOpenAI]:
    """Constrói o grafo do agente e o juiz com clientes reais (lidos de settings)."""
    s = get_settings()
    openai_client = OpenAI(api_key=s.openai_api_key or "sk-absent")
    qdrant = QdrantClient(url=s.qdrant_url)
    ro_engine = criar_engine(s.agente_ro_url)

    deps = Dependencias(
        llm=criar_llm(
            openai_client, modelo_forte=s.llm_model_forte, modelo_rapido=s.llm_model_rapido
        ),
        executar_sql=executor_run_sql(
            ro_engine, max_rows=s.max_rows, statement_timeout_ms=s.statement_timeout_ms
        ),
        qdrant=cast(ClienteQdrant, qdrant),
        embedder=criar_embedder(openai_client, model=s.embed_model, dim=s.embed_dim),
        hoje=s.hoje_ancora,
    )
    grafo = construir_grafo(deps)
    juiz = JuizOpenAI(openai_client, modelo=s.llm_model_forte)
    return grafo, juiz


def _imprimir_scorecard(rel: RelatorioEval) -> None:
    """Tabela legível no terminal — o resumo que um humano lê de relance."""
    a = rel.agregado
    print("\n=== Scorecard EDD (qualidade da resposta do produto) ===")
    print(f"{'caso':<26} {'rota':<5} {'recall':<7} {'distr':<6} {'exec':<5} {'faith':<5}")
    for c in rel.casos:
        p = c.pontuacao
        print(
            f"{c.id:<26} {'ok' if p.roteamento_ok else 'X':<5} "
            f"{p.recall_fontes:<7.2f} {p.distratores_citados:<6} "
            f"{'ok' if p.execucao_ok else 'X':<5} {c.faithfulness:<5.2f}"
        )
    faith = f"{a.faithfulness_media:.2f}" if a.faithfulness_media is not None else "—"
    print(
        f"\nAGREGADO (n={a.n_casos}): roteamento {a.roteamento_ok}/{a.n_casos} · "
        f"recall central {a.recall_medio_central:.2f} (global {a.recall_medio:.2f}) · "
        f"sem-distrator {a.casos_sem_distrator}/{a.n_casos} · "
        f"execução {a.execucao_ok}/{a.n_casos} · faithfulness média {faith}"
    )


async def _principal(out: Path) -> None:
    casos = carregar_golden()
    grafo, juiz = _montar_grafo_e_juiz()
    rel = await rodar_eval(casos, grafo=grafo, juiz=juiz)
    _imprimir_scorecard(rel)
    out.write_text(json.dumps(rel.como_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport completo (inspecionável) gravado em: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate de avaliação EDD do agente.")
    parser.add_argument(
        "--out", type=Path, default=Path("eval-report.json"), help="caminho do report JSON"
    )
    args = parser.parse_args()
    asyncio.run(_principal(args.out))


if __name__ == "__main__":
    main()
