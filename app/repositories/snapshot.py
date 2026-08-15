"""Snapshot writes. The snapshot body is built from the persisted row in SQL."""

from __future__ import annotations

from typing import Any

from app.domain import tables
from app.gateway.port import PgGateway
from app.repositories.base import BaseRepository


class SnapshotRepository(BaseRepository):
    def __init__(self, gateway: PgGateway) -> None:
        super().__init__(gateway, None)

    async def create(self, agentic_workflow_id: str, comment: str) -> dict[str, Any]:
        return await self.call(tables.CREATE_SNAPSHOT, agentic_workflow_id, comment)
