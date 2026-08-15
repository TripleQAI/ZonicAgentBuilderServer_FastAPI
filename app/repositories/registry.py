"""Node-type and tool repositories, plus the deployed-schema read."""

from __future__ import annotations

from typing import Any

from app.domain import tables
from app.gateway.port import PgGateway
from app.repositories.base import BaseRepository, as_json_arg


class NodeTypeRepository(BaseRepository):
    def __init__(self, gateway: PgGateway) -> None:
        super().__init__(gateway, tables.NODE_TYPE)

    async def list_active(self) -> list[dict[str, Any]]:
        return await self.list()

    async def upsert_all(self, definitions: list[dict[str, Any]]) -> int:
        """Seed the whole registry in one round trip, not one call per type."""
        row = await self.call(tables.UPSERT_NODE_TYPES, as_json_arg(definitions))
        return int(row.get("o_count") or 0)


class ToolRepository(BaseRepository):
    def __init__(self, gateway: PgGateway) -> None:
        super().__init__(gateway, tables.TOOL)

    async def list_active(self) -> list[dict[str, Any]]:
        return await self.list()

    async def upsert_all(self, definitions: list[dict[str, Any]]) -> int:
        row = await self.call(tables.UPSERT_TOOLS, as_json_arg(definitions))
        return int(row.get("o_count") or 0)


class SchemaRepository(BaseRepository):
    def __init__(self, gateway: PgGateway) -> None:
        super().__init__(gateway, tables.SCHEMA_MIGRATION)

    async def deployed_versions(self) -> list[str]:
        return [str(row["version"]) for row in await self.list()]
