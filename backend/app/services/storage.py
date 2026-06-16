"""Persistencia dos artefatos do run no MinIO (issue #23).

Grava o relatorio (markdown) e o spec do grafico (JSON) sob o prefixo do `run_id`,
num bucket proprio (`relatorios`) — nunca no `corpus` pre-populado, que e sagrado.

O SDK `minio` e sincrono; toda chamada de rede roda em `asyncio.to_thread` para nao
bloquear o event loop (regra de async ponta a ponta). O cliente e criado uma vez e
reusado (thread-safe; ao contrario dos clientes async de Postgres/Qdrant).
"""

from __future__ import annotations

import asyncio
import io
import json
from typing import Any

from minio import Minio

from app.config import settings

_client: Minio | None = None


def _minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
    return _client


def _put(client: Minio, bucket: str, key: str, data: bytes, content_type: str) -> None:
    """Garante o bucket e grava o objeto (sincrono — chamado via to_thread)."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)


async def persistir_artefatos(
    run_id: str,
    relatorio_md: str,
    grafico_spec: dict[str, Any] | None,
) -> dict[str, str]:
    """Persiste relatorio (+grafico, se houver) e devolve as chaves `bucket/objeto`."""
    client = _minio()
    bucket = settings.minio_bucket_relatorios
    artefatos: dict[str, str] = {}

    rel_key = f"{run_id}/relatorio.md"
    await asyncio.to_thread(
        _put, client, bucket, rel_key, relatorio_md.encode("utf-8"), "text/markdown"
    )
    artefatos["relatorio"] = f"{bucket}/{rel_key}"

    if grafico_spec is not None:
        graf_key = f"{run_id}/grafico.json"
        payload = json.dumps(grafico_spec, ensure_ascii=False).encode("utf-8")
        await asyncio.to_thread(_put, client, bucket, graf_key, payload, "application/json")
        artefatos["grafico"] = f"{bucket}/{graf_key}"

    return artefatos
