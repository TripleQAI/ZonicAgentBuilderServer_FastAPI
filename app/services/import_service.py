"""Package import. Ported from ``agentBuilder/services/agent_importer.py``.

The whole package — root, every child and every relationship — is written by a
single procedure call, so a failed import leaves nothing behind. The Django
implementation wrote row by row and could leave a package half-imported.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.domain.schemas.agent import ImportResult
from app.repositories.agent_workflow import AgentWorkflowRepository
from app.services import agent_mapping, relationship_service


class ImportService:
    def __init__(self, agents: AgentWorkflowRepository) -> None:
        self._agents = agents

    async def import_package(
        self,
        root_agent_json: dict[str, Any],
        sub_agents_json: list[dict[str, Any]] | None = None,
        parent_package_id: str | None = None,
    ) -> ImportResult:
        package_id = parent_package_id or str(uuid.uuid4())
        warnings: list[str] = []

        root_json, root_id = agent_mapping.ensure_workflow_id(root_agent_json)

        sub_columns: list[dict[str, Any]] = []
        child_ids: list[str] = []
        seen: set[str] = set()

        for sub_json in sub_agents_json or []:
            workflow_id = sub_json.get("agenticWorkflowId")
            if not workflow_id:
                warnings.append("Sub-agent entry missing agenticWorkflowId — skipped")
                continue
            workflow_id = str(workflow_id)
            if workflow_id in seen:
                warnings.append(
                    f"Duplicate agenticWorkflowId {workflow_id} in sub_agents — skipped"
                )
                continue
            seen.add(workflow_id)
            child_ids.append(workflow_id)
            sub_columns.append(
                agent_mapping.to_columns(
                    sub_json,
                    agentic_workflow_id=workflow_id,
                    is_root=False,
                    parent_package_id=package_id,
                    replace_raw_json=True,
                )
            )

        relationships, rel_warnings = relationship_service.derive_for_import(
            root_json.get("nodes") or [], seen
        )
        warnings.extend(rel_warnings)

        root_columns = agent_mapping.to_columns(
            root_json,
            agentic_workflow_id=root_id,
            is_root=True,
            parent_package_id=package_id,
            replace_raw_json=True,
        )

        result = await self._agents.import_package(root_columns, sub_columns, relationships)

        return ImportResult(
            root_agent_id=root_id,
            sub_agent_ids=child_ids,
            relationship_count=int(result.get("o_relationship_count") or 0),
            warnings=warnings,
            parent_package_id=package_id,
        )
