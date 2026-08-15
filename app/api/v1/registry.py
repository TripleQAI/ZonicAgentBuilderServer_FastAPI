"""Node-type and tool registry routes.

Both prefer the database table and fall back to the JSON resources when it is
empty — the same precedence the Django views had, so an unseeded deployment
still serves a working palette.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.deps import NodeTypeRepoDep, ToolRepoDep
from app.core.errors import DataUnavailableError
from app.domain.schemas.workflow import (
    NodeTypeDefinition,
    NodeTypeListResponse,
    ToolDefinition,
    ToolListResponse,
)
from app.registry.loader import load_option_sets, load_seed_tools, to_api_rows

logger = logging.getLogger(__name__)

router = APIRouter(tags=["registry"])


@router.get("/node-types", response_model=NodeTypeListResponse, summary="Node type registry")
async def node_types(repo: NodeTypeRepoDep) -> NodeTypeListResponse:
    try:
        rows = await repo.list_active()
    except DataUnavailableError:
        logger.warning("node type table unreadable; serving the JSON registry")
        rows = []

    if rows:
        definitions = [
            NodeTypeDefinition(
                type=r["type"],
                label=r["label"],
                icon=r.get("icon") or "",
                color=r.get("color") or "",
                description=r.get("description") or "",
                default_name_prefix=r.get("default_name_prefix") or "",
                default_config=r.get("default_config") or {},
                handles=r.get("handles") or {},
                form_schema=r.get("form_schema") or {},
                output_schema=r.get("output_schema") or {},
                validation_schema=r.get("validation_schema") or {},
                sort_order=int(r.get("sort_order") or 0),
            )
            for r in rows
        ]
    else:
        definitions = [NodeTypeDefinition.model_validate(r) for r in to_api_rows()]

    return NodeTypeListResponse(node_types=definitions)


@router.get(
    "/option-sets",
    response_model=dict[str, list[dict[str, str]]],
    summary="Shared select-option lists",
)
async def option_sets() -> dict[str, list[dict[str, str]]]:
    """Option lists the UI renders in list widgets and settings panels.

    Serving them keeps one definition: the source repeated these across
    node_registry.py, dynamic_fields.js and the page template.
    """
    return load_option_sets()


@router.get("/tools", response_model=ToolListResponse, summary="Tool catalogue")
async def tools(repo: ToolRepoDep) -> ToolListResponse:
    try:
        rows = await repo.list_active()
    except DataUnavailableError:
        logger.warning("tool table unreadable; serving the JSON seed catalogue")
        rows = []

    source = rows or load_seed_tools()
    return ToolListResponse(
        tools=[
            ToolDefinition(
                name=t["name"],
                title=t.get("title") or "",
                description=t.get("description") or "",
                tool_type=t.get("tool_type") or "function",
                schema=t.get("schema") or {},
                default_config=t.get("default_config") or {},
            )
            for t in source
        ]
    )
