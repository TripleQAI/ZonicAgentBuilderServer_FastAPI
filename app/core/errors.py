"""The application error hierarchy and its HTTP envelope.

One shape for every failure, so clients parse one thing. The ``error`` key is
kept from the Django surface; ``code`` and ``traceId`` are additive
(MIGRATION_PLAN.md §7.5).
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base for everything this service raises deliberately."""

    status_code: int = 500
    code: str = "internal"

    def __init__(self, message: str, *, details: Any = None, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        self.headers = headers or {}

    def to_body(self, trace_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.message, "code": self.code}
        if self.details is not None:
            body["details"] = self.details
        if trace_id:
            body["traceId"] = trace_id
        return body


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    """No sign-in, or a token that is invalid or expired: the UI sends the user to sign in."""

    status_code = 401
    code = "unauthorized"


class AuthNotConfiguredError(AppError):
    """Sign-in is required but the user pool is not configured (COGNITO_* settings)."""

    status_code = 503
    code = "auth_not_configured"


class InvalidRequestError(AppError):
    status_code = 400
    code = "invalid_request"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class UpstreamError(AppError):
    """A dependency failed in a way the caller cannot fix (gateway, Bedrock)."""

    status_code = 502
    code = "upstream_failure"


class DataUnavailableError(AppError):
    """The data path is temporarily unreachable. Retryable."""

    status_code = 503
    code = "data_unavailable"
