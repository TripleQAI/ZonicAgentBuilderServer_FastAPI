"""Relationship reads. Writes happen inside the agent save/import procedures."""

from __future__ import annotations

from typing import Any

from app.domain import tables
from app.gateway.models import Filter, FilterOp
from app.gateway.port import PgGateway
from app.repositories.base import BaseRepository


class AgentRelationshipRepository(BaseRepository):
    def __init__(self, gateway: PgGateway) -> None:
        super().__init__(gateway, tables.RELATIONSHIP_DETAIL)

    async def for_parent(self, parent_agentic_workflow_id: str) -> list[dict[str, Any]]:
        """The whole relationship map, child details included, in ONE read."""
        return await self.list(
            [
                Filter(
                    column="parent_agentic_workflow_id",
                    op=FilterOp.EQ,
                    value=parent_agentic_workflow_id,
                )
            ]
        )
