"""seed/ingest.py — ingestão offline determinística (corpus -> MinIO -> Qdrant).

Invariante #1: a ingestão é offline, determinística e **sem agente / sem LLM
raciocinando**. O embedding é vetorização, não "o agente".

Embeddings: **OpenAI `text-embedding-3-large` (3072 dims)** — exige `OPENAI_API_KEY`
(rede + custo). Vetores calculados via SDK e gravados no Qdrant com `upsert`
(coleções criadas explicitamente com 3072 dims, distância de cosseno).

Fluxo (PRD §7.1):
  - `diagnostico` / `prescricao`: lê seed/corpus/<col>/*.md (frontmatter §8.3 +
    corpo), sobe o **bruto** para o MinIO (bucket `corpus`), faz chunk + embed e
    indexa no Qdrant com o payload §8.3.
  - `camada_semantica`: gerada a partir do schema (definições de KPI + exemplos
    pergunta->SQL) e indexada **direto** no Qdrant — não vai para o MinIO.

Idempotente: recria as coleções a cada run.

Pré-requisitos:
    docker compose up -d qdrant minio
    # OPENAI_API_KEY no .env (ou no ambiente)
Uso:
    uv run python seed/ingest.py
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path

import yaml
from minio import Minio
from openai import OpenAI
from qdrant_client import QdrantClient, models

RAIZ = Path(__file__).resolve().parents[1]
CORPUS_DIR = Path(__file__).parent / "corpus"

EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-large")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "3072"))

CHUNK_CHARS = 900
CHUNK_OVERLAP = 150

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_PASS = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
BUCKET = os.environ.get("MINIO_BUCKET", "corpus")

# campos do payload §8.3 que filtram a busca (chave -> tipo de índice no Qdrant)
_KW = models.PayloadSchemaType.KEYWORD
_INT = models.PayloadSchemaType.INTEGER
INDICES = {
    "tipo": _KW, "subtipo": _KW, "periodo_referencia": _KW,
    "ano": _INT, "mes": _INT, "regiao": _KW, "produto": _KW,
    "canal": _KW, "kpi_alvo": _KW, "resultado": _KW,
}


# --------------------------------------------------------------------------- #
def carrega_env() -> None:
    """Carrega .env no os.environ (sem sobrescrever o que já está no ambiente)."""
    env = RAIZ / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]  # remove aspas que envolvem o valor (gotcha comum de .env)
        os.environ.setdefault(k.strip(), v)


def parse_doc(path: Path) -> tuple[dict, str]:
    """Separa frontmatter YAML (payload) do corpo (texto a indexar)."""
    raw = path.read_text(encoding="utf-8")
    _, frontmatter, body = raw.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return meta, body.strip()


def chunk(texto: str) -> list[str]:
    """Janela deslizante simples por caracteres (docs curtos -> 1-2 chunks)."""
    if len(texto) <= CHUNK_CHARS:
        return [texto]
    out, i = [], 0
    while i < len(texto):
        out.append(texto[i:i + CHUNK_CHARS])
        i += CHUNK_CHARS - CHUNK_OVERLAP
    return out


def limpa_payload(meta: dict) -> dict:
    """Remove chaves nulas (filtro fica mais limpo)."""
    return {k: v for k, v in meta.items() if v is not None}


def embed(oai: OpenAI, textos: list[str]) -> list[list[float]]:
    """Embeddings via OpenAI, em lotes. Vetores de EMBED_DIM dims."""
    vetores: list[list[float]] = []
    lote = 100
    for i in range(0, len(textos), lote):
        resp = oai.embeddings.create(
            model=EMBED_MODEL, input=textos[i:i + lote], dimensions=EMBED_DIM
        )
        vetores.extend(d.embedding for d in resp.data)
    return vetores


def espera(nome: str, ping, tentativas: int = 30) -> None:
    for n in range(tentativas):
        try:
            ping()
            return
        except Exception as e:  # noqa: BLE001
            if n == tentativas - 1:
                raise SystemExit(f"{nome} não respondeu após {tentativas}s: {e}")
            time.sleep(1)


def camada_semantica_docs() -> list[tuple[str, dict]]:
    """Definições de métricas/tabelas + exemplos pergunta->SQL (texto, payload)."""
    base = {"tipo": "camada_semantica", "fonte": "schema://negocio"}
    return [
        ("KPI faturamento: receita de pedidos pagos. SQL: "
         "SELECT sum(valor_total) FROM negocio.pedidos WHERE status='pago'. "
         "Faturamento por categoria usa a receita dos itens "
         "(sum(quantidade*preco_unitario) em itens_pedido).",
         {**base, "subtipo": "metrica", "kpi_alvo": "faturamento"}),
        ("KPI ticket_medio: faturamento dividido pelo número de pedidos pagos. SQL: "
         "sum(valor_total)/count(*) FROM negocio.pedidos WHERE status='pago'.",
         {**base, "subtipo": "metrica", "kpi_alvo": "ticket_medio"}),
        ("KPI taxa_recompra: fração de pedidos feitos por clientes que já compraram "
         "antes. Um pedido é recompra se EXISTS pedido anterior do mesmo cliente_id "
         "com data_pedido menor. Recorte usual por regiao.",
         {**base, "subtipo": "metrica", "kpi_alvo": "taxa_recompra"}),
        ("KPI taxa_conversao: pedidos divididos por sessões (tráfego). SQL: "
         "count(pedidos)/sum(sessoes_diarias.sessoes), por canal e período. "
         "sessoes_diarias é o denominador (visitas por canal x regiao x dia).",
         {**base, "subtipo": "metrica", "kpi_alvo": "taxa_conversao"}),
        ("Esquema negocio: pedidos(id, cliente_id, canal_id, regiao_id, data_pedido, "
         "status, valor_total) é o fato; itens_pedido(pedido_id, produto_id, "
         "quantidade, preco_unitario) é o detalhe; dimensões regioes, canais, "
         "categorias, produtos, clientes; metas(ano, mes, kpi, regiao_id, canal_id, "
         "categoria_id, valor_meta) define o alvo. Junte produtos->categorias para "
         "recorte por categoria; pedidos.regiao_id é denormalizado.",
         {**base, "subtipo": "tabela"}),
        ("Exemplo pergunta->SQL. Pergunta: faturamento por canal no último mês. SQL: "
         "SELECT c.nome, sum(p.valor_total) FROM negocio.pedidos p JOIN negocio.canais "
         "c ON c.id=p.canal_id WHERE p.status='pago' AND p.data_pedido >= "
         "date_trunc('month', current_date) GROUP BY 1.",
         {**base, "subtipo": "exemplo_sql", "kpi_alvo": "faturamento"}),
        ("Exemplo pergunta->SQL. Pergunta: taxa de recompra por regiao. SQL: WITH ped "
         "AS (SELECT p.regiao_id, (EXISTS (SELECT 1 FROM negocio.pedidos a WHERE "
         "a.cliente_id=p.cliente_id AND a.data_pedido<p.data_pedido))::int r FROM "
         "negocio.pedidos p) SELECT regiao_id, avg(r) FROM ped GROUP BY 1.",
         {**base, "subtipo": "exemplo_sql", "kpi_alvo": "taxa_recompra"}),
    ]


def main() -> None:
    carrega_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY ausente. Defina no .env (ou no ambiente) para gerar os "
            "embeddings com OpenAI. Ex.: OPENAI_API_KEY=sk-..."
        )

    print(f"Conectando (embeddings: {EMBED_MODEL}, {EMBED_DIM}d)...")
    oai = OpenAI()
    qc = QdrantClient(url=QDRANT_URL)
    mc = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)
    espera("Qdrant", qc.get_collections)
    espera("MinIO", mc.list_buckets)

    if not mc.bucket_exists(BUCKET):
        mc.make_bucket(BUCKET)
        print(f"  bucket MinIO '{BUCKET}' criado")

    next_id = 1

    def indexa(colecao: str, itens: list[tuple[str, dict]]) -> None:
        nonlocal next_id
        if qc.collection_exists(colecao):
            qc.delete_collection(colecao)  # idempotência: recria do zero
        qc.create_collection(
            colecao,
            vectors_config=models.VectorParams(size=EMBED_DIM, distance=models.Distance.COSINE),
        )
        docs, payloads, ids = [], [], []
        for texto, meta in itens:
            for j, pedaco in enumerate(chunk(texto)):
                docs.append(pedaco)
                payloads.append({**limpa_payload(meta), "document": pedaco, "chunk": j})
                ids.append(next_id)
                next_id += 1
        vetores = embed(oai, docs)
        qc.upsert(colecao, points=[
            models.PointStruct(id=i, vector=v, payload=p)
            for i, v, p in zip(ids, vetores, payloads)
        ])
        for campo, tipo in INDICES.items():
            try:
                qc.create_payload_index(colecao, field_name=campo, field_schema=tipo)
            except Exception:  # noqa: BLE001
                pass
        print(f"  {colecao:<16} {len(docs):>3} chunks de {len(itens)} documentos")

    # camada_semantica: direto do schema (sem MinIO)
    print("Indexando coleções no Qdrant:")
    indexa("camada_semantica", camada_semantica_docs())

    # diagnostico / prescricao: corpus .md -> MinIO (bruto) -> Qdrant
    for colecao in ("diagnostico", "prescricao"):
        itens: list[tuple[str, dict]] = []
        for path in sorted((CORPUS_DIR / colecao).glob("*.md")):
            meta, body = parse_doc(path)
            data = path.read_bytes()
            mc.put_object(BUCKET, f"{colecao}/{path.name}",
                          io.BytesIO(data), length=len(data),
                          content_type="text/markdown")
            itens.append((body, meta))
        indexa(colecao, itens)

    _verifica(qc, oai)
    print("Ingestão concluída.")


def _verifica(qc: QdrantClient, oai: OpenAI) -> None:
    print("\nVerificação — buscas filtradas (§8.3):")

    def busca(titulo, colecao, query, **filtros):
        conds = [models.FieldCondition(key=k, match=models.MatchValue(value=v))
                 for k, v in filtros.items()]
        flt = models.Filter(must=conds) if conds else None
        qv = embed(oai, [query])[0]
        res = qc.query_points(collection_name=colecao, query=qv,
                              query_filter=flt, limit=3).points
        print(f"\n  [{colecao}] '{query}'  filtros={filtros}")
        for r in res:
            fonte = (r.payload or {}).get("fonte", "?")
            print(f"     score={r.score:.3f}  {fonte}")

    busca("N1", "diagnostico", "atrasos na entrega e queda de recompra", regiao="Sul")
    busca("N1 presc", "prescricao", "como recuperar a recompra", kpi_alvo="taxa_recompra")
    busca("N2 presc", "prescricao", "defender faturamento sem queimar margem",
          produto="Eletrônicos", canal="marketplace")
    busca("sazonal nov", "prescricao", "playbook de faturamento na black friday", mes=11)
    busca("semantica", "camada_semantica", "como calcular a taxa de recompra")


if __name__ == "__main__":
    main()
