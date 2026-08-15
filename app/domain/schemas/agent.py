"""Agent request and response models.

Shapes match the Django surface exactly — the frontend and the golden fixtures
both depend on them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.schemas.base import CamelModel


class AgentSummary(CamelModel):
    """One row of GET /agents."""

    agentic_workflow_id: str
    name: str = ""
    display_name: str = ""
    is_root: bool = False
    node_count: int = 0
    edge_count: int = 0
    environment: str = ""
    updated_at: datetime | None = None


class AgentListResponse(CamelModel):
    agents: list[AgentSummary] = Field(default_factory=list)


class SaveResult(CamelModel):
    status: str = "saved"
    agentic_workflow_id: str
    relationship_count: int = 0
    node_count: int = 0
    edge_count: int = 0


class SnapshotResult(CamelModel):
    snapshot_id: str
    agentic_workflow_id: str
    created_at: datetime | None = None


class EmbedResult(CamelModel):
    status: str = "indexed"
    agentic_workflow_id: str
    dimensions: int
    text_length: int


class ImportRequest(CamelModel):
    """JSON body form of the import endpoint. The multipart form is handled in
    the router, matching the Django view which accepted either."""

    agent_data: dict[str, Any] | None = None
    sub_agents_data: list[dict[str, Any]] | None = None


class ImportResult(CamelModel):
    # snake_case on the wire: the Django endpoint returned these key names and
    # main.js reads them directly, so they are pinned by parity, not by style.
    root_agent_id: str = Field(serialization_alias="root_agent_id")
    sub_agent_ids: list[str] = Field(default_factory=list, serialization_alias="sub_agent_ids")
    relationship_count: int = Field(0, serialization_alias="relationship_count")
    warnings: list[str] = Field(default_factory=list, serialization_alias="warnings")
    parent_package_id: str = Field("", serialization_alias="parent_package_id")


class ChildAgentRef(CamelModel):
    agentic_workflow_id: str
    name: str = ""
    display_name: str = ""
    node_count: int = 0
    edge_count: int = 0


class RelationshipEntry(CamelModel):
    source_node_id: str = ""
    source_node_name: str = ""
    child_agentic_workflow_id: str
    is_resolved: bool = False
    child_agent: ChildAgentRef | None = None
    validation_message: str | None = None


class UnreferencedAgent(CamelModel):
    agentic_workflow_id: str
    name: str = ""
    display_name: str = ""


class RelationshipMap(CamelModel):
    root_agent_id: str
    root_agent_name: str = ""
    resolved_count: int = 0
    unresolved_count: int = 0
    resolved: list[RelationshipEntry] = Field(default_factory=list)
    unresolved: list[RelationshipEntry] = Field(default_factory=list)
    unreferenced_sub_agents: list[UnreferencedAgent] = Field(default_factory=list)
