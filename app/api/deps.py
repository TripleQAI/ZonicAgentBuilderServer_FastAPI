"""Dependency wiring. Composition happens here and nowhere else."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.core.auth import CognitoVerifier, User, bearer_token
from app.gateway.port import PgGateway
from app.repositories.agent_relationship import AgentRelationshipRepository
from app.repositories.agent_workflow import AgentWorkflowRepository
from app.repositories.registry import NodeTypeRepository, SchemaRepository, ToolRepository
from app.repositories.snapshot import SnapshotRepository
from app.services.agent_service import AgentService
from app.services.embedding.port import EmbeddingProvider
from app.services.embedding.service import EmbeddingService
from app.services.export_service import ExportService
from app.services.import_service import ImportService

SettingsDep = Annotated[Settings, Depends(get_settings)]

#: Who a request runs as when sign-in is switched off (AUTH_REQUIRED=false).
LOCAL_USER = User(sub="local", email="")


def get_current_user(request: Request) -> User:
    """The signed-in user, from the request's Cognito ID token (app/core/auth.py).

    A plain function, so FastAPI runs it in its thread pool: the first call
    fetches the pool's signing keys.
    """
    settings: Settings = request.app.state.settings
    if not settings.auth_required:
        return LOCAL_USER
    token = bearer_token(request.headers.get("authorization"))
    verifier = request.app.state.verifier
    if verifier is None:
        verifier = request.app.state.verifier = CognitoVerifier(settings)
    return verifier.verify(token)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_gateway(request: Request) -> PgGateway:
    """The single gateway instance created by the lifespan."""
    return request.app.state.gateway  # type: ignore[no-any-return]


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    return request.app.state.embedding_provider  # type: ignore[no-any-return]


GatewayDep = Annotated[PgGateway, Depends(get_gateway)]
ProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]


def get_agent_repo(gateway: GatewayDep) -> AgentWorkflowRepository:
    return AgentWorkflowRepository(gateway)


def get_relationship_repo(gateway: GatewayDep) -> AgentRelationshipRepository:
    return AgentRelationshipRepository(gateway)


def get_snapshot_repo(gateway: GatewayDep) -> SnapshotRepository:
    return SnapshotRepository(gateway)


def get_node_type_repo(gateway: GatewayDep) -> NodeTypeRepository:
    return NodeTypeRepository(gateway)


def get_tool_repo(gateway: GatewayDep) -> ToolRepository:
    return ToolRepository(gateway)


def get_schema_repo(gateway: GatewayDep) -> SchemaRepository:
    return SchemaRepository(gateway)


AgentRepoDep = Annotated[AgentWorkflowRepository, Depends(get_agent_repo)]
RelationshipRepoDep = Annotated[AgentRelationshipRepository, Depends(get_relationship_repo)]
SnapshotRepoDep = Annotated[SnapshotRepository, Depends(get_snapshot_repo)]
NodeTypeRepoDep = Annotated[NodeTypeRepository, Depends(get_node_type_repo)]
ToolRepoDep = Annotated[ToolRepository, Depends(get_tool_repo)]


def get_agent_service(agents: AgentRepoDep, snapshots: SnapshotRepoDep) -> AgentService:
    return AgentService(agents, snapshots)


def get_import_service(agents: AgentRepoDep) -> ImportService:
    return ImportService(agents)


def get_export_service(agents: AgentRepoDep, relationships: RelationshipRepoDep) -> ExportService:
    return ExportService(agents, relationships)


def get_embedding_service(agents: AgentRepoDep, provider: ProviderDep) -> EmbeddingService:
    return EmbeddingService(agents, provider)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]
ExportServiceDep = Annotated[ExportService, Depends(get_export_service)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
