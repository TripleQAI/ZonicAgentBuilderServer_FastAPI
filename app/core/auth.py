"""Sign-in: who is calling, from a Cognito ID token.

The builder has its own Cognito user pool, separate from the Strands Visual
Builder's. The UI signs the user in against it and sends the ID token as
``Authorization: Bearer <token>``; this module checks the token's signature
(the pool's published keys), issuer, audience (the app client), expiry and use.

Nothing below the API layer reads token claims: routes get a ``User``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

from app.config import Settings
from app.core.errors import AuthNotConfiguredError, UnauthorizedError

#: Clock skew allowed between Cognito and this server, in seconds.
LEEWAY_SECONDS = 30


@dataclass(frozen=True)
class User:
    #: Cognito subject: stable for the life of the user, unlike the email.
    sub: str
    email: str


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    """One key client per pool; it caches the keys and refetches on an unknown key ID."""
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)


class CognitoVerifier:
    """Checks a Cognito ID token for the configured pool and app client."""

    def __init__(self, settings: Settings, keys: Any | None = None) -> None:
        if not settings.cognito_user_pool_id or not settings.cognito_app_client_id:
            raise AuthNotConfiguredError(
                "Sign-in is not configured: set COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID."
            )
        self._issuer = settings.cognito_issuer
        self._audience = settings.cognito_app_client_id
        #: Anything with ``get_signing_key_from_jwt(token).key``; tests pass their own.
        self._keys = keys or _jwks_client(f"{self._issuer}/.well-known/jwks.json")

    def verify(self, token: str) -> User:
        try:
            key = self._keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Your session has expired. Sign in again.") from exc
        except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
            raise UnauthorizedError("Sign-in required.") from exc
        # An access token has no audience claim and would fail above; check the use anyway.
        if claims.get("token_use") != "id":
            raise UnauthorizedError("Sign-in required.")
        return User(sub=str(claims["sub"]), email=str(claims.get("email", "")))


def bearer_token(authorization: str | None) -> str:
    """The token of an ``Authorization: Bearer <token>`` header."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Sign-in required.", headers={"WWW-Authenticate": "Bearer"})
    return token.strip()
