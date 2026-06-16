# seed/ — dataset sintético + corpus + ingestão

(Re)gera ~5 anos de vendas de um e-commerce de varejo no **Postgres** e o corpus
qualitativo no **MinIO**/**Qdrant**, ambos com as **narrativas plantadas** descritas
em [`NARRATIVAS.md`](./NARRATIVAS.md) (decisão D3). É o **triplo** completo:
padrão quantitativo (Postgres) ↔ `diagnostico` ↔ `prescricao` → golden dataset.

## Arquivos
- `schema.sql`   — DDL do schema `negocio` (dimensões + fatos + `metas`).
- `generate.py`  — gerador **determinístico** (Faker). Escreve CSVs em `seed/data/`.
- `load.py`      — aplica o schema e faz COPY dos CSVs no Postgres (idempotente).
- `corpus/`      — documentos `.md` (frontmatter §8.3 + corpo): `diagnostico/` e `prescricao/`.
- `ingest.py`    — sobe o corpus pro MinIO e indexa as 3 coleções no Qdrant (idempotente).
- `NARRATIVAS.md`— o "enredo" de cada narrativa, para revisão humana.
- Golden dataset derivado: [`../evals/golden/narrativas.yaml`](../evals/golden/narrativas.yaml).

## Uso
```bash
docker compose up -d postgres qdrant minio   # stores no ar (precisa do .env: cp .env.example .env)

# 1) Postgres (vendas + metas)
uv run python seed/generate.py                # gera seed/data/*.csv (regenerável; não versionado)
uv run python seed/load.py                    # cria negocio.* e carrega; sanity das narrativas

# 2) Corpus qualitativo (MinIO -> Qdrant)
uv run python seed/ingest.py                  # upload + embed + index; verifica buscas filtradas
```

Consoles: MinIO em http://localhost:9001 (user/senha do `.env`, default `minioadmin`);
Qdrant em http://localhost:6333/dashboard.

## Notas
- **Somente leitura para o agente** (invariantes #2/#3): o seed usa conexões admin
  (RW); quem cria/popula nunca é o agente. A ingestão é **offline e sem LLM** (#1).
- **Embeddings:** `fastembed` local (modelo EN pequeno, p/ rodar offline na POC).
  Para PT em produção, troque `EMBED_MODEL` por um multilíngue (ex.: multilingual-e5).
- **Promoção a migration:** em produção o `schema.sql` deve virar migration Alembic
  em `infra/db/migrations/**`, sob revisão humana (regra `backend.md`).
- Parâmetros de escala/seed ficam no topo de `generate.py`.
