"""Sign-in: every /api/v1 route needs a valid Cognito ID token for the builder's
own pool and app client; /health stays open. Tokens here are signed with a key
made for the test, standing in for the pool's published keys."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.core.auth import CognitoVerifier
from app.gateway.fake import FakeGateway
from app.main import create_app
from app.services.embedding.service import FakeEmbeddingProvider

POOL = "us-east-1_TestPool"
CLIENT = "builder-test-client"
ISSUER = f"https://cognito-idp.us-east-1.amazonaws.com/{POOL}"

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class _SigningKey:
    key: Any


class FakeKeys:
    """The pool's published keys: one key, found by its key ID."""

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        if jwt.get_unverified_header(token).get("kid") != "test":
            raise jwt.PyJWKClientError("Unable to find a signing key that matches")
        return _SigningKey(KEY.public_key())


def token(**overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "user-1",
        "email": "builder@example.com",
        "iss": ISSUER,
        "aud": CLIENT,
        "token_use": "id",
        "iat": now,
        "exp": now + 3600,
    }
    key = overrides.pop("key", KEY)
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test"})


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "pg_gateway_provider": "fake",
        "embedding_provider": "fake",
        "seed_registry_on_startup": False,
        "auth_required": True,
        "cognito_user_pool_id": POOL,
        "cognito_app_client_id": CLIENT,
    }
    values.update(overrides)
    return Settings(**values)


async def _client(config: Settings, verifier: CognitoVerifier | None) -> AsyncIterator[AsyncClient]:
    app = create_app(
        config, gateway=FakeGateway(), embedding_provider=FakeEmbeddingProvider(), verifier=verifier
    )
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client,
        app.router.lifespan_context(app),
    ):
        yield http_client


@pytest_asyncio.fixture
async def secured() -> AsyncIterator[AsyncClient]:
    config = settings()
    async for http_client in _client(config, CognitoVerifier(config, keys=FakeKeys())):
        yield http_client


def bearer(value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {value}"}


async def test_a_signed_in_user_reaches_the_api(secured: AsyncClient) -> None:
    response = await secured.get("/api/v1/me", headers=bearer(token()))
    assert response.status_code == 200, response.text
    assert response.json() == {"sub": "user-1", "email": "builder@example.com"}
    assert (await secured.get("/api/v1/agents", headers=bearer(token()))).status_code == 200


async def test_no_token_is_401_and_health_stays_open(secured: AsyncClient) -> None:
    response = await secured.get("/api/v1/agents")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
    assert response.headers["www-authenticate"] == "Bearer"
    assert (await secured.get("/health")).status_code == 200


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(token(key=OTHER_KEY), id="signed by another key"),
        pytest.param(token(aud="strands-visual-builder-client"), id="another app client"),
        pytest.param(
            token(iss="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Other"),
            id="another pool",
        ),
        pytest.param(token(token_use="access"), id="an access token"),
        pytest.param("not-a-jwt", id="garbage"),
    ],
)
async def test_tokens_not_for_this_builder_are_refused(secured: AsyncClient, bad: str) -> None:
    response = await secured.get("/api/v1/agents", headers=bearer(bad))
    assert response.status_code == 401, response.text


async def test_an_expired_token_says_so(secured: AsyncClient) -> None:
    old = int(time.time()) - 7200
    response = await secured.get("/api/v1/agents", headers=bearer(token(iat=old, exp=old + 3600)))
    assert response.status_code == 401
    assert "expired" in response.json()["error"]


async def test_a_missing_user_pool_is_reported_not_crashed() -> None:
    async for http_client in _client(settings(cognito_user_pool_id=""), None):
        response = await http_client.get("/api/v1/agents", headers=bearer(token()))
        assert response.status_code == 503
        assert response.json()["code"] == "auth_not_configured"
