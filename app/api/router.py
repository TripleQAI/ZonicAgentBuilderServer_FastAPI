"""Aggregates the v1 surface."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import agents, registry, workflows

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(agents.router)
api_router.include_router(registry.router)
api_router.include_router(workflows.router)
