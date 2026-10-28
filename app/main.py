"""Application factory and lifespan.

A factory, not a module-level app: tests build their own instance with the
gateway and embedding provider overridden (MIGRATION_PLAN.md §5).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.v1 import health
from app.config import Settings, get_settings
from app.core.auth import CognitoVerifier
from app.core.errors import AppError
from app.gateway.fake import FakeGateway
from app.gateway.http import HttpPgGateway
from app.gateway.port import PgGateway
from app.registry.seeder import seed
from app.services.embedding.bedrock import BedrockEmbeddingProvider
from app.services.embedding.port import EmbeddingProvider
from app.services.embedding.service import FakeEmbeddingProvider

logger = logging.getLogger(__name__)


def build_gateway(settings: Settings) -> PgGateway:
    if settings.pg_gateway_provider == "fake":
        return FakeGateway()
    return HttpPgGateway(settings)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider()
    return BedrockEmbeddingProvider(
        region=settings.bedrock_region, model_id=settings.bedrock_embed_model_id
    )


def create_app(
    settings: Settings | None = None,
    *,
    gateway: PgGateway | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    verifier: CognitoVerifier | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    logging.basicConfig(level=resolved.log_level.upper())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved
        # Built on first use (get_current_user), so a service without a user pool
        # still starts and answers /health; sign-in calls then say what is missing.
        app.state.verifier = verifier
        app.state.gateway = gateway or build_gateway(resolved)
        app.state.embedding_provider = embedding_provider or build_embedding_provider(
            resolved
        )
        if resolved.seed_registry_on_startup:
            await seed(app.state.gateway)
        try:
            yield
        finally:
            await app.state.gateway.aclose()

    app = FastAPI(
        title="Zonic Agent Workflow Builder API",
        version="1.0.0",
        description=(
            "Visual multi-agent workflow builder. Persistence goes through the "
            "pgfoundation SQL gateway; this service holds no database driver."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlate(request: Request, call_next):  # type: ignore[no-untyped-def]
        trace_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = trace_id
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            exc.to_body(trace_id), status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Reshaped into the same envelope so clients parse one error format.
        return JSONResponse(
            {
                "error": "Request validation failed",
                "code": "invalid_request",
                "details": exc.errors(),
                "traceId": getattr(request.state, "trace_id", None),
            },
            status_code=400,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None)
        logger.exception("unhandled error traceId=%s", trace_id)
        return JSONResponse(
            {"error": "Internal server error", "code": "internal", "traceId": trace_id},
            status_code=500,
        )

    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
