"""The embedding port. Business logic depends on this, never on boto3."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]:
        """Return a document embedding for ``text``."""
        ...
