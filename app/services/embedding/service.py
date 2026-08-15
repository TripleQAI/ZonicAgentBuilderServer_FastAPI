"""Embedding text construction and storage.

``build_embedding_text`` is ported verbatim from the Django service — the text
it produces is the semantic fingerprint, so changing it silently invalidates
every stored vector.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

from app.core.errors import InvalidRequestError, NotFoundError
from app.domain.schemas.agent import EmbedResult
from app.registry.loader import load_option_sets
from app.repositories.agent_workflow import AgentWorkflowRepository
from app.services.embedding.port import EmbeddingProvider

_DIMENSIONS = 1024


def _domain_labels() -> dict[str, str]:
    """Labels come from the shared option set the UI also renders, so the two
    cannot disagree about what a domain is called."""
    return {o["value"]: o["label"] for o in load_option_sets().get("semanticDomains", [])}


def build_embedding_text(agent: dict[str, Any]) -> str:
    """Concatenate workflow metadata into one document string."""
    parts = [f"Workflow: {agent.get('displayName') or agent.get('name') or ''}"]
    if agent.get("description"):
        parts.append(f"Description: {agent['description']}")
    domain = agent.get("semanticDomain")
    if domain:
        parts.append(f"Domain: {_domain_labels().get(domain, domain)}")
    if agent.get("semanticKeywords"):
        parts.append(f"Keywords: {agent['semanticKeywords']}")
    if agent.get("semanticUseCases"):
        parts.append(f"Use cases: {agent['semanticUseCases']}")
    nodes = agent.get("nodes") or []
    node_types = sorted({n.get("type", "") for n in nodes if n.get("type")})
    if node_types:
        parts.append(f"Node types: {', '.join(node_types)}")
    return "\n".join(parts)


class FakeEmbeddingProvider:
    """Deterministic unit vector derived from the text. No network, no AWS."""

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [
            ((digest[i % len(digest)] + i) % 255) / 255.0 - 0.5
            for i in range(_DIMENSIONS)
        ]
        norm = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / norm for v in raw]


class EmbeddingService:
    def __init__(
        self, agents: AgentWorkflowRepository, provider: EmbeddingProvider
    ) -> None:
        self._agents = agents
        self._provider = provider

    async def embed_and_store(self, agentic_workflow_id: str) -> EmbedResult:
        row = await self._agents.get_detail(agentic_workflow_id)
        if row is None:
            raise NotFoundError("Agent not found")
        if not row.get("semantic_search_enabled"):
            raise InvalidRequestError(
                "Semantic search is not enabled for this workflow."
            )

        # Embed the persisted state, not the request body.
        detail = dict(row["detail_json"])
        text = build_embedding_text(detail)
        vector = await self._provider.embed(text)

        await self._agents.store_embedding(agentic_workflow_id, vector, text)

        return EmbedResult(
            agentic_workflow_id=agentic_workflow_id,
            dimensions=len(vector),
            text_length=len(text),
        )
