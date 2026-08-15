"""Agent routes. Thin: parse, delegate, return."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import (
    AgentRepoDep,
    AgentServiceDep,
    EmbeddingServiceDep,
    ExportServiceDep,
    ImportServiceDep,
    RelationshipRepoDep,
)
from app.core.errors import InvalidRequestError, NotFoundError
from app.domain.schemas.agent import (
    AgentListResponse,
    EmbedResult,
    ImportResult,
    RelationshipMap,
    SaveResult,
    SnapshotResult,
)
from app.services import relationship_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse, summary="List agent workflows")
async def list_agents(service: AgentServiceDep) -> AgentListResponse:
    return AgentListResponse(agents=await service.list_summaries())


@router.post(
    "/import-package",
    response_model=ImportResult,
    status_code=201,
    summary="Import an agent package",
)
async def import_package(
    request: Request,
    service: ImportServiceDep,
    agent_file: Annotated[UploadFile | None, File()] = None,
    sub_agents_file: Annotated[UploadFile | None, File()] = None,
) -> ImportResult:
    """Accepts multipart (agent_file + optional sub_agents_file) or a JSON body
    with agent_data / sub_agents_data, exactly as the Django endpoint did."""
    content_type = request.headers.get("content-type", "")

    if "multipart" in content_type:
        if agent_file is None:
            raise InvalidRequestError("agent_file is required")
        root = _parse_json(await agent_file.read(), "agent_file")
        subs = (
            _parse_json(await sub_agents_file.read(), "sub_agents_file")
            if sub_agents_file
            else None
        )
    else:
        body = _parse_json(await request.body(), "request body")
        root = body.get("agent_data")
        if not root:
            raise InvalidRequestError("agent_data is required")
        subs = body.get("sub_agents_data")

    if subs is not None and not isinstance(subs, list):
        raise InvalidRequestError("sub_agents must be an array")

    return await service.import_package(root, subs)


@router.get("/{agentic_workflow_id}", summary="Get one agent workflow")
async def get_agent(agentic_workflow_id: str, service: AgentServiceDep) -> JSONResponse:
    # The response is the agent's own JSON document, not a fixed model — unknown
    # keys from raw_json must survive the round trip.
    return JSONResponse(await service.get_detail(agentic_workflow_id))


@router.put(
    "/{agentic_workflow_id}", response_model=SaveResult, summary="Create or update an agent"
)
async def save_agent(
    agentic_workflow_id: str, request: Request, service: AgentServiceDep
) -> SaveResult:
    body = _parse_json(await request.body(), "request body")
    if not isinstance(body, dict):
        raise InvalidRequestError("request body must be a JSON object")
    return await service.save(agentic_workflow_id, body)


@router.get(
    "/{agentic_workflow_id}/relationships",
    response_model=RelationshipMap,
    summary="Parent-to-child relationship map",
)
async def agent_relationships(
    agentic_workflow_id: str,
    agents: AgentRepoDep,
    relationships: RelationshipRepoDep,
) -> RelationshipMap:
    detail = await agents.get_detail(agentic_workflow_id)
    if detail is None:
        raise NotFoundError(f"Agent {agentic_workflow_id} not found")

    rows = await relationships.for_parent(agentic_workflow_id)
    package_id = detail.get("parent_package_id")
    members = (
        await agents.list_package_members(str(package_id)) if package_id else []
    )

    return relationship_service.build_map(
        agentic_workflow_id, detail.get("name") or "", rows, members
    )


@router.get("/{agentic_workflow_id}/export", summary="Export one agent")
async def export_agent(agentic_workflow_id: str, service: ExportServiceDep) -> JSONResponse:
    return JSONResponse(await service.export_single(agentic_workflow_id))


@router.get("/{agentic_workflow_id}/export-package", summary="Export agent + children")
async def export_agent_package(
    agentic_workflow_id: str, service: ExportServiceDep
) -> JSONResponse:
    return JSONResponse(await service.export_package(agentic_workflow_id))


@router.get("/{agentic_workflow_id}/export-debug", summary="Export package + warnings")
async def export_agent_debug(
    agentic_workflow_id: str, service: ExportServiceDep
) -> JSONResponse:
    return JSONResponse(await service.export_debug(agentic_workflow_id))


@router.post(
    "/{agentic_workflow_id}/snapshots",
    response_model=SnapshotResult,
    status_code=201,
    summary="Create a workflow snapshot",
)
async def create_snapshot(
    agentic_workflow_id: str, request: Request, service: AgentServiceDep
) -> SnapshotResult:
    raw = await request.body()
    body = _parse_json(raw, "request body") if raw else {}
    comment = body.get("comment", "") if isinstance(body, dict) else ""
    return await service.create_snapshot(agentic_workflow_id, comment)


@router.post(
    "/{agentic_workflow_id}/embed",
    response_model=EmbedResult,
    summary="Generate and store the semantic embedding",
)
async def embed_agent(
    agentic_workflow_id: str, service: EmbeddingServiceDep
) -> EmbedResult:
    return await service.embed_and_store(agentic_workflow_id)


def _parse_json(raw: bytes, what: str) -> Any:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidRequestError(f"Invalid JSON in {what}: {exc}") from exc
