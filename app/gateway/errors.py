"""Anti-corruption layer: pgfoundation failures -> this service's error model.

pgfoundation returns ``{"error", "type", "request_id"}`` with its own status
mapping. Nothing above ``app/gateway`` should ever see that vocabulary, so the
translation happens here, once (MIGRATION_PLAN.md §7.5).

The reasoning behind the mapping is worth stating, because the obvious
pass-through is wrong: a 400 from the gateway means *we* composed a bad
governed call. That is our defect, not the browser's, so it must not surface to
the browser as a 400.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.errors import AppError, ConflictError, DataUnavailableError, UpstreamError

logger = logging.getLogger(__name__)

#: gateway status -> our exception class.
_STATUS_MAP: dict[int, type[AppError]] = {
    400: UpstreamError,   # malformed governed call — our bug
    401: UpstreamError,   # our service credential is wrong
    403: UpstreamError,
    404: UpstreamError,   # unknown data source — misconfiguration
    409: ConflictError,   # genuine constraint violation
    413: UpstreamError,   # result too large; unreachable for our read sizes
    422: UpstreamError,   # batch too large
    503: DataUnavailableError,
}


def _describe(status: int, body: Any) -> tuple[str, str | None]:
    """Pull ``error`` / ``type`` / ``request_id`` out of the gateway envelope."""
    if isinstance(body, dict):
        message = str(body.get("error") or body.get("detail") or body)
        gateway_type = body.get("type")
        request_id = body.get("request_id")
    else:
        message = str(body)
        gateway_type = None
        request_id = None
    if gateway_type:
        message = f"{gateway_type}: {message}"
    logger.warning(
        "gateway error status=%s type=%s request_id=%s message=%s",
        status, gateway_type, request_id, message,
    )
    return message, request_id


def translate_status(
    status: int, body: Any, *, headers: dict[str, str] | None = None
) -> AppError:
    """Map an error response onto an :class:`AppError`. Never raises."""
    message, _ = _describe(status, body)
    # Anything unmapped is an upstream failure: the caller cannot act on it.
    error_cls = _STATUS_MAP.get(status, UpstreamError)

    forwarded: dict[str, str] = {}
    if headers and (retry_after := headers.get("retry-after")):
        forwarded["Retry-After"] = retry_after

    return error_cls(f"data gateway: {message}", headers=forwarded)


def translate_transport(exc: Exception) -> AppError:
    """A connection failure or timeout is a temporary data-path outage."""
    logger.warning("gateway transport failure: %s", exc)
    return DataUnavailableError(f"data gateway unreachable: {exc}")
