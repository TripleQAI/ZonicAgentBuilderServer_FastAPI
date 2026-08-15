"""Validation, mock-run and registry response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.schemas.base import CamelModel


class ValidationResult(BaseModel):
    """snake_case on the wire: validation.js reads node_count / edge_count."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class MockTraceEntry(CamelModel):
    node_id: str | None = None
    node_type: str | None = None
    node_name: str = ""
    status: str = "mock_executed"


class MockRunResult(CamelModel):
    status: str = "mock_completed"
    message: str = ""
    node_count: int = 0
    trace: list[MockTraceEntry] = Field(default_factory=list)


class NodeTypeDefinition(CamelModel):
    type: str
    label: str
    icon: str = ""
    color: str = ""
    description: str = ""
    default_name_prefix: str = ""
    default_config: dict[str, Any] = Field(default_factory=dict)
    handles: dict[str, Any] = Field(default_factory=dict)
    form_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    validation_schema: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0


class NodeTypeListResponse(CamelModel):
    node_types: list[NodeTypeDefinition] = Field(default_factory=list)


class ToolDefinition(CamelModel):
    name: str
    title: str = ""
    description: str = ""
    tool_type: str = "function"
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    default_config: dict[str, Any] = Field(default_factory=dict)


class ToolListResponse(CamelModel):
    tools: list[ToolDefinition] = Field(default_factory=list)


class HealthResponse(CamelModel):
    status: str
    gateway: str
    datasource: str
