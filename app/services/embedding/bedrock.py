"""AWS Bedrock adapter — Cohere Embed English v3.

Ported from ``agentBuilder/services/embedding_service.py``. boto3 is blocking,
so the call runs in a worker thread, and boto3 is imported lazily so the package
stays optional.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core.errors import UpstreamError


class BedrockEmbeddingProvider:
    def __init__(self, *, region: str, model_id: str) -> None:
        self._region = region
        self._model_id = model_id

    def _invoke(self, text: str) -> list[float]:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - depends on the install extra
            raise UpstreamError(
                "boto3 is required for embedding generation: pip install '.[embedding]'"
            ) from exc

        client = boto3.client("bedrock-runtime", region_name=self._region)
        body = json.dumps(
            {"texts": [text], "input_type": "search_document", "truncate": "END"}
        )
        try:
            response: Any = client.invoke_model(
                modelId=self._model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
        except Exception as exc:
            raise UpstreamError(f"Bedrock invocation failed: {exc}") from exc

        embeddings = payload.get("embeddings")
        if not embeddings or not embeddings[0]:
            raise UpstreamError(f"Unexpected Bedrock response shape: {payload}")
        return list(embeddings[0])

    async def embed(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._invoke, text)
