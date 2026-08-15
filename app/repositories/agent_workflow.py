"""Reads and writes for the agent aggregate."""

from __future__ import annotations

from typing import Any

from app.domain import tables
from app.gateway.models import Filter, FilterOp
from app.gateway.port import PgGateway
from app.repositories.base import BaseRepository, as_json_arg

UNRESOLVED_MESSAGE_FMT = "Child workflow %s not found in database"
"""Wording owned by the application, passed to SQL so the message stays here."""


class AgentWorkflowRepository(BaseRepository):
    def __init__(self, gateway: PgGateway) -> None:
        super().__init__(gateway, tables.AGENT_SUMMARY)

    # -- reads -------------------------------------------------------------

    async def list_summaries(self) -> list[dict[str, Any]]:
        return await self.list()

    async def get_detail(self, agentic_workflow_id: str) -> dict[str, Any] | None:
        return await self.get_by(
            "agentic_workflow_id", agentic_workflow_id, spec=tables.AGENT_DETAIL
        )

    async def get_export(self, agentic_workflow_id: str) -> dict[str, Any] | None:
        return await self.get_by(
            "agentic_workflow_id", agentic_workflow_id, spec=tables.AGENT_EXPORT
        )

    async def list_exports(self, agentic_workflow_ids: list[str]) -> list[dict[str, Any]]:
        """Every child export in one read — the Django code issues one per child."""
        return await self.list_in(
            "agentic_workflow_id", agentic_workflow_ids, spec=tables.AGENT_EXPORT
        )

    async def list_package_members(
        self, parent_package_id: str, *, include_root: bool = False
    ) -> list[dict[str, Any]]:
        filters = [
            Filter(column="parent_package_id", op=FilterOp.EQ, value=parent_package_id)
        ]
        if not include_root:
            filters.append(Filter(column="is_root", op=FilterOp.EQ, value=False))
        return await self.list(filters, spec=tables.PACKAGE_AGENT)

    # -- writes ------------------------------------------------------------

    async def save(
        self, agent_columns: dict[str, Any], relationships: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Agent + chip + relationships in one transaction."""
        return await self.call(
            tables.SAVE_AGENT,
            as_json_arg(agent_columns),
            as_json_arg(relationships),
            UNRESOLVED_MESSAGE_FMT,
        )

    async def import_package(
        self,
        root_columns: dict[str, Any],
        sub_agent_columns: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Root + children + relationships in one transaction."""
        return await self.call(
            tables.IMPORT_PACKAGE,
            as_json_arg(root_columns),
            as_json_arg(sub_agent_columns),
            as_json_arg(relationships),
            UNRESOLVED_MESSAGE_FMT,
        )

    async def store_embedding(
        self, agentic_workflow_id: str, vector: list[float], text: str
    ) -> dict[str, Any]:
        return await self.call(
            tables.STORE_EMBEDDING, agentic_workflow_id, as_json_arg(vector), text
        )
