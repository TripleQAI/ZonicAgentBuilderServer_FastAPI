"""Aggregates the v1 surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1 import agents, me, registry, workflows

# Every v1 route needs a signed-in user; /health stays open for probes.
api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_user)])
api_router.include_router(me.router)
api_router.include_router(agents.router)
api_router.include_router(registry.router)
api_router.include_router(workflows.router)
