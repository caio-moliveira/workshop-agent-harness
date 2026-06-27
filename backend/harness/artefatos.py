"""Armazenamento de artefatos (relatório, SQL) no MinIO — inspecionáveis pelo analista.

A interface `Artefatos` é injetável: produção usa MinIO; teste usa um fake em memória.
O cliente MinIO é síncrono — `to_thread` evita bloquear o event loop.
"""

from __future__ import annotations

import asyncio
import io
from typing import Protocol

from minio import Minio


class Artefatos(Protocol):
    """Contrato mínimo: grava um texto e devolve a URI rastreável."""

    async def gravar_texto(self, caminho: str, conteudo: str, *, content_type: str) -> str: ...


class ArtefatosMinio:
    """Implementação MinIO. Garante o bucket e devolve `minio://<bucket>/<caminho>`."""

    def __init__(self, client: Minio, *, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def gravar_texto(self, caminho: str, conteudo: str, *, content_type: str) -> str:
        dados = conteudo.encode("utf-8")

        def _put() -> None:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
            self._client.put_object(
                self._bucket,
                caminho,
                io.BytesIO(dados),
                length=len(dados),
                content_type=content_type,
            )

        await asyncio.to_thread(_put)
        return f"minio://{self._bucket}/{caminho}"
