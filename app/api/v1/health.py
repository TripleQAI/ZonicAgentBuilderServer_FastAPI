"""Liveness and readiness.

Liveness is true while the process is up. Readiness reports the data path
honestly: if the gateway cannot be reached, this service is not ready, and says
so rather than failing opaquely on the first request.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import GatewayDep, SettingsDep
from app.domain.schemas.workflow import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness")
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        gateway=settings.pg_gateway_base_url,
        datasource=settings.pg_gateway_datasource,
    )


@router.get("/health/ready", response_model=HealthResponse, summary="Readiness")
async def ready(
    gateway: GatewayDep, settings: SettingsDep, response: Response
) -> HealthResponse:
    ok = await gateway.ready()
    if not ok:
        response.status_code = 503
    return HealthResponse(
        status="ready" if ok else "down",
        gateway=settings.pg_gateway_base_url,
        datasource=settings.pg_gateway_datasource,
    )
