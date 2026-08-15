"""Workflow utilities: validation and the legacy server-side mock run."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request

from app.core.errors import InvalidRequestError
from app.domain.schemas.workflow import MockRunResult, MockTraceEntry, ValidationResult
from app.services.validation.engine import validate_workflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/validate", response_model=ValidationResult, summary="Validate a workflow")
async def validate(request: Request) -> ValidationResult:
    body = _parse(await request.body())
    if not isinstance(body, dict):
        raise InvalidRequestError("request body must be a JSON object")
    return validate_workflow(body)


@router.post(
    "/run-mock",
    response_model=MockRunResult,
    summary="Server-side mock run (deprecated)",
    deprecated=True,
    description=(
        "Kept for parity with the Django surface. The real mock engine is "
        "client-side; this returns a per-node stub, exactly as before."
    ),
)
async def run_mock(request: Request) -> MockRunResult:
    body = _parse(await request.body())
    nodes = (body or {}).get("nodes") or []
    return MockRunResult(
        message=(
            "Mock execution completed. No real LLMs or external tools were called."
        ),
        node_count=len(nodes),
        trace=[
            MockTraceEntry(
                node_id=n.get("id"),
                node_type=n.get("type"),
                node_name=n.get("name", ""),
            )
            for n in nodes
        ],
    )


def _parse(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidRequestError(f"Invalid JSON: {exc}") from exc
