"""seed/load.py — aplica o schema de negócio e carrega os CSVs no Postgres.

Ferramenta de HOST (não roda dentro do container da API). Usa a conexão admin
(RW) de `DATABASE_URL` — o usuário read-only do agente nunca escreve (invariante
#2/#3). Idempotente: dá TRUNCATE e recarrega, então pode rodar quantas vezes quiser.

Pré-requisitos:
    docker compose up -d postgres          # Postgres no ar (localhost:5432)
    uv run python seed/generate.py         # gera os CSVs em seed/data/

Uso:
    uv run python seed/load.py
"""

from __future__ import annotations

import asyncio
import csv
import os
from pathlib import Path

import asyncpg

RAIZ = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).parent / "data"
SCHEMA_SQL = Path(__file__).parent / "schema.sql"

# ordem de carga (pais antes dos filhos, por causa das FKs)
TABELAS = [
    "regioes", "canais", "categorias", "produtos", "clientes",
    "pedidos", "itens_pedido", "sessoes_diarias", "metas",
]


def resolver_dsn() -> str:
    """DATABASE_URL do ambiente ou do .env; normaliza para o formato do asyncpg."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        env = RAIZ / ".env"
        if env.exists():
            for linha in env.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if linha.startswith("DATABASE_URL=") and "#" not in linha.split("=", 1)[0]:
                    url = linha.split("=", 1)[1].strip()
                    break
    if not url:
        raise SystemExit(
            "DATABASE_URL não encontrada. Copie .env.example para .env "
            "(cp .env.example .env) ou exporte DATABASE_URL."
        )
    # asyncpg não entende o dialeto SQLAlchemy 'postgresql+asyncpg://'
    return url.replace("+asyncpg", "")


async def carregar() -> None:
    if not (DATA_DIR / "pedidos.csv").exists():
        raise SystemExit("CSVs ausentes em seed/data/. Rode antes: uv run python seed/generate.py")

    conn = await asyncpg.connect(resolver_dsn())
    try:
        print("Aplicando schema (negocio.*)...")
        await conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

        # idempotência: limpa tudo antes de recarregar
        await conn.execute(
            "TRUNCATE " + ", ".join(f"negocio.{t}" for t in reversed(TABELAS))
            + " RESTART IDENTITY CASCADE;"
        )

        print("Carregando (COPY):")
        for tabela in TABELAS:
            caminho = DATA_DIR / f"{tabela}.csv"
            with caminho.open("r", encoding="utf-8") as f:
                colunas = next(csv.reader(f))  # cabeçalho -> nomes das colunas
            with caminho.open("rb") as f:
                await conn.copy_to_table(
                    tabela, source=f, schema_name="negocio", columns=colunas,
                    format="csv", header=True, encoding="utf-8",
                )
            n = await conn.fetchval(f"SELECT count(*) FROM negocio.{tabela}")
            print(f"  {tabela:<16} {n:>8,} linhas")

        await _sanity(conn)
    finally:
        await conn.close()
    print("Carga concluída.")


async def _sanity(conn: asyncpg.Connection) -> None:
    """Espia rápida: confirma que as narrativas plantadas aparecem nos números."""
    print("\nSanity / narrativas plantadas:")

    fat_ano = await conn.fetch(
        "SELECT extract(year FROM data_pedido)::int AS ano, "
        "       round(sum(valor_total)/1e6, 2) AS fat_milhoes "
        "FROM negocio.pedidos WHERE status='pago' GROUP BY 1 ORDER BY 1"
    )
    print("  Faturamento (R$ mi) por ano:",
          ", ".join(f"{r['ano']}={r['fat_milhoes']}" for r in fat_ano))

    # N1 — recompra no Sul: 1º semestre 2025 vs 2026
    recompra = await conn.fetch(
        """
        WITH base AS (
            SELECT p.id, p.regiao_id, extract(year FROM p.data_pedido)::int AS ano,
                   (EXISTS (SELECT 1 FROM negocio.pedidos a
                            WHERE a.cliente_id = p.cliente_id
                              AND a.data_pedido < p.data_pedido)) AS recompra
            FROM negocio.pedidos p
            JOIN negocio.regioes r ON r.id = p.regiao_id
            WHERE r.nome = 'Sul' AND extract(month FROM p.data_pedido) BETWEEN 1 AND 6
        )
        SELECT ano, round(avg(recompra::int)::numeric, 3) AS taxa_recompra
        FROM base WHERE ano IN (2025, 2026) GROUP BY ano ORDER BY ano
        """
    )
    print("  N1 recompra Sul (1ºsem):",
          ", ".join(f"{r['ano']}={r['taxa_recompra']}" for r in recompra))

    # N2 — Eletrônicos × marketplace no Q4: 2024 vs 2025
    n2 = await conn.fetch(
        """
        SELECT extract(year FROM p.data_pedido)::int AS ano,
               round(sum(i.quantidade*i.preco_unitario)/1e3, 1) AS receita_mil
        FROM negocio.itens_pedido i
        JOIN negocio.pedidos p   ON p.id = i.pedido_id AND p.status='pago'
        JOIN negocio.produtos pr ON pr.id = i.produto_id
        JOIN negocio.categorias c ON c.id = pr.categoria_id
        JOIN negocio.canais ca   ON ca.id = p.canal_id
        WHERE c.nome='Eletrônicos' AND ca.nome='marketplace'
          AND extract(month FROM p.data_pedido) IN (10,11,12)
        GROUP BY 1 HAVING extract(year FROM p.data_pedido)::int IN (2024,2025) ORDER BY 1
        """
    )
    print("  N2 Eletrônicos×marketplace Q4 (R$ mil):",
          ", ".join(f"{r['ano']}={r['receita_mil']}" for r in n2))


if __name__ == "__main__":
    asyncio.run(carregar())
