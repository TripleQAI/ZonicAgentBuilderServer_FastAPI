"""Agent read/save orchestration."""

from __future__ import annotations

from typing import Any

from app.core.errors import NotFoundError
from app.domain.schemas.agent import AgentSummary, SaveResult, SnapshotResult
from app.repositories.agent_workflow import AgentWorkflowRepository
from app.repositories.snapshot import SnapshotRepository
from app.services import agent_mapping, relationship_service


class AgentService:
    def __init__(
        self, agents: AgentWorkflowRepository, snapshots: SnapshotRepository
    ) -> None:
        self._agents = agents
        self._snapshots = snapshots

    async def list_summaries(self) -> list[AgentSummary]:
        rows = await self._agents.list_summaries()
        return [AgentSummary.model_validate(_stringify_id(row)) for row in rows]

    async def get_detail(self, agentic_workflow_id: str) -> dict[str, Any]:
        row = await self._agents.get_detail(agentic_workflow_id)
        if row is None:
            raise NotFoundError("Agent not found")
        # detail_json already carries the raw_json overlay — the view owns that
        # rule so it cannot drift from the export path.
        return dict(row["detail_json"])

    async def save(self, agentic_workflow_id: str, body: dict[str, Any]) -> SaveResult:
        """PUT /agents/{id}. Upsert, exactly as the Django view did.

        Agent, chip and relationships land in one transaction — the source used
        a non-atomic ``asyncio.gather``.
        """
        columns = agent_mapping.to_columns(
            body, agentic_workflow_id=agentic_workflow_id, replace_raw_json=False
        )
        if not await self._agents.get_detail(agentic_workflow_id):
            # New rows are roots and need the Django view's creation defaults.
            columns.setdefault("name", body.get("name", "new-workflow"))
            columns.setdefault("display_name", body.get("displayName", "New Workflow"))
            columns["is_root"] = True

        # Relationships are derived from the canvas. If the caller did not send
        # one, the stored canvas is unchanged, so the stored edges are still
        # correct — pass None and the procedure leaves them alone. Deriving from
        # an absent body would delete every edge on a partial save.
        relationships = (
            relationship_service.derive_for_save(body["nodes"] or [], agentic_workflow_id)
            if "nodes" in body
            else None
        )

        result = await self._agents.save(columns, relationships)
        return SaveResult(
            agentic_workflow_id=agentic_workflow_id,
            relationship_count=int(result.get("o_relationship_count") or 0),
            node_count=int(result.get("o_node_count") or 0),
            edge_count=int(result.get("o_edge_count") or 0),
        )

    async def create_snapshot(
        self, agentic_workflow_id: str, comment: str
    ) -> SnapshotResult:
        if not await self._agents.get_detail(agentic_workflow_id):
            raise NotFoundError("Agent not found")
        row = await self._snapshots.create(agentic_workflow_id, comment)
        return SnapshotResult(
            snapshot_id=str(row.get("o_snapshot_id")),
            agentic_workflow_id=agentic_workflow_id,
            created_at=row.get("o_created_at"),
        )


def _stringify_id(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["agentic_workflow_id"] = str(out["agentic_workflow_id"])
    return out
