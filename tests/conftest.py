"""Test wiring.

The whole unit suite runs against :class:`FakeGateway` — no database, no
gateway process, no AWS. Live integration tests opt in with ``-m live``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.gateway.fake import FakeGateway
from app.main import create_app
from app.services.embedding.service import FakeEmbeddingProvider

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def agent_json() -> dict[str, Any]:
    return json.loads((FIXTURES / "agent.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sub_agents_json() -> list[dict[str, Any]]:
    return json.loads((FIXTURES / "sub_agents.json").read_text(encoding="utf-8"))


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        pg_gateway_provider="fake",
        embedding_provider="fake",
        seed_registry_on_startup=False,
        cors_origins="http://localhost:3000",
        # Sign-in has its own tests (tests/unit/test_auth.py); the rest run as one local user.
        auth_required=False,
    )


@pytest_asyncio.fixture
async def client(settings: Settings, gateway: FakeGateway) -> AsyncIterator[AsyncClient]:
    app = create_app(
        settings, gateway=gateway, embedding_provider=FakeEmbeddingProvider()
    )
    # The lifespan populates app.state; the client speaks to the app in-process.
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client,
        app.router.lifespan_context(app),
    ):
        yield http_client
