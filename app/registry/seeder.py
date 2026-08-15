"""Push the JSON registry into the database at startup.

Idempotent, one round trip per table. Failure is logged and swallowed: the
registry endpoints fall back to the JSON resources, so a gateway that is not
yet up must not stop the service from booting.
"""

from __future__ import annotations

import logging

from app.gateway.port import PgGateway
from app.registry.loader import load_seed_tools, to_db_rows
from app.repositories.registry import NodeTypeRepository, ToolRepository

logger = logging.getLogger(__name__)


async def seed(gateway: PgGateway) -> None:
    try:
        node_count = await NodeTypeRepository(gateway).upsert_all(to_db_rows())
        tool_count = await ToolRepository(gateway).upsert_all(load_seed_tools())
    except Exception as exc:
        logger.warning("registry seeding skipped: %s", exc)
        return
    logger.info("registry seeded: %d node types, %d tools", node_count, tool_count)
