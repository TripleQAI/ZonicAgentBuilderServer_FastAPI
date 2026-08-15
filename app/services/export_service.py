"""Export. Ported from ``agentBuilder/services/agent_exporter.py``.

The raw_json overlay is not recomputed here — ``v_agent_export`` owns it, so
``/export`` and ``/export-package`` cannot disagree. Children are fetched in one
read instead of one per child.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import NotFoundError
from app.repositories.agent_relationship import AgentRelationshipRepository
from app.repositories.agent_workflow import AgentWorkflowRepository


class ExportService:
    def __init__(
        self,
        agents: AgentWorkflowRepository,
        relationships: AgentRelationshipRepository,
    ) -> None:
        self._agents = agents
        self._relationships = relationships

    async def export_single(self, agentic_workflow_id: str) -> dict[str, Any]:
        row = await self._agents.get_export(agentic_workflow_id)
        if row is None:
            raise NotFoundError(f"Agent {agentic_workflow_id} not found")
        return dict(row["export_json"])

    async def export_package(self, root_agentic_workflow_id: str) -> dict[str, Any]:
        root_row = await self._agents.get_export(root_agentic_workflow_id)
        if root_row is None:
            raise NotFoundError(f"Root agent {root_agentic_workflow_id} not found")

        rows = await self._relationships.for_parent(root_agentic_workflow_id)

        relationship_map = [
            {
                "sourceNodeId": r.get("source_node_id") or "",
                "sourceNodeName": r.get("source_node_name") or "",
                "parentAgenticWorkflowId": str(r.get("parent_agentic_workflow_id")),
                "childAgenticWorkflowId": str(r.get("child_agentic_workflow_id")),
                "isResolved": bool(r.get("is_resolved")),
                "validationMessage": r.get("validation_message") or "",
            }
            for r in rows
        ]

        # Preserve first-seen order, drop duplicates — the Django loop's behaviour.
        child_ids: list[str] = []
        for r in rows:
            if not r.get("is_resolved") or r.get("child_name") is None:
                continue
            child_id = str(r["child_agentic_workflow_id"])
            if child_id not in child_ids:
                child_ids.append(child_id)

        child_rows = await self._agents.list_exports(child_ids)
        by_id = {str(row["agentic_workflow_id"]): row["export_json"] for row in child_rows}
        sub_agents = [dict(by_id[cid]) for cid in child_ids if cid in by_id]

        return {
            "agent": dict(root_row["export_json"]),
            "sub_agents": sub_agents,
            "relationshipMap": relationship_map,
        }

    async def export_debug(self, root_agentic_workflow_id: str) -> dict[str, Any]:
        base = await self.export_package(root_agentic_workflow_id)
        warnings: list[str] = []

        root_row = await self._agents.get_export(root_agentic_workflow_id)
        rows = await self._relationships.for_parent(root_agentic_workflow_id)

        for r in rows:
            if not r.get("is_resolved"):
                warnings.append(
                    f"Unresolved sub-agent: node '{r.get('source_node_name') or ''}' "
                    f"references {r.get('child_agentic_workflow_id')} which is not imported"
                )

        referenced = {
            str(r["child_agentic_workflow_id"]) for r in rows if r.get("is_resolved")
        }
        package_id = root_row.get("parent_package_id") if root_row else None
        if package_id:
            for member in await self._agents.list_package_members(str(package_id)):
                member_id = str(member["agentic_workflow_id"])
                if member_id not in referenced:
                    label = member.get("display_name") or member.get("name") or ""
                    warnings.append(
                        f"Unreferenced sub-agent: '{label}' ({member_id}) "
                        f"is imported but not referenced"
                    )

        base["warnings"] = warnings
        return base
