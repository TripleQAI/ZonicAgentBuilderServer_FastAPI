"""HTTP adapter for the pgfoundation gateway.

The only module in this project that knows pgfoundation exists.

Retry policy is deliberately narrow: reads retry on 503 and transport failure;
**writes never retry here**. The gateway already retries serialization failures
and deadlocks at the transaction level, which is the correct granularity — a
second retry layer above it would re-run a committed procedure.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import Settings
from app.gateway import routes
from app.gateway.errors import translate_status, translate_transport
from app.gateway.models import (
    BatchItem,
    BatchRequest,
    BatchResult,
    Filter,
    FunctionIn,
    OrderBy,
    ProcedureIn,
    QueryOut,
    ViewIn,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {503}


class HttpPgGateway:
    """Implements :class:`~app.gateway.port.PgGateway` over HTTP."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._datasource = settings.pg_gateway_datasource
        # Stamped onto every payload. Callers never pass a schema, so there is
        # one place the deployment's schema is decided, and no dependency on the
        # connection's search_path.
        self._schema = settings.pg_gateway_schema or None
        self._max_retries = settings.pg_gateway_max_retries
        self._owns_client = client is None
        headers = {"content-type": "application/json"}
        if settings.pg_gateway_auth_header:
            name, _, value = settings.pg_gateway_auth_header.partition(":")
            headers[name.strip() or "authorization"] = value.strip()
        self._client = client or httpx.AsyncClient(
            base_url=settings.pg_gateway_base_url,
            timeout=httpx.Timeout(
                settings.pg_gateway_timeout_ms / 1000,
                connect=settings.pg_gateway_connect_timeout_ms / 1000,
            ),
            headers=headers,
        )

    # -- transport ---------------------------------------------------------

    async def _post(
        self, path: str, payload: dict[str, Any], *, retry: bool, trace_id: str | None = None
    ) -> Any:
        url = path.format(datasource=self._datasource)
        attempts = (self._max_retries + 1) if retry else 1
        last: Exception | None = None

        for attempt in range(attempts):
            try:
                headers = {"X-Request-Id": trace_id} if trace_id else None
                response = await self._client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                last = translate_transport(exc)
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise last from exc

            if response.status_code < 400:
                return response.json()

            body = _safe_json(response)
            if response.status_code in _RETRYABLE_STATUS and attempt + 1 < attempts:
                await asyncio.sleep(0.05 * (2**attempt))
                continue
            raise translate_status(
                response.status_code, body, headers=dict(response.headers)
            )

        raise last or translate_transport(RuntimeError("no attempt was made"))

    # -- operations --------------------------------------------------------

    async def view(
        self,
        name: str,
        *,
        columns: list[str] | None = None,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        trace_id: str | None = None,
    ) -> QueryOut:
        payload = ViewIn(
            name=name,
            db_schema=self._schema,
            columns=columns,
            filters=filters or [],
            order_by=order_by or [],
            limit=limit,
            offset=offset,
        ).model_dump(mode="json", by_alias=True, exclude_none=True)
        data = await self._post(routes.VIEW, payload, retry=True, trace_id=trace_id)
        return QueryOut.model_validate(data)

    async def procedure(
        self, name: str, args: list[Any] | None = None, *, trace_id: str | None = None
    ) -> QueryOut:
        payload = ProcedureIn(name=name, db_schema=self._schema, args=args).model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
        # retry=False: a procedure is a write.
        data = await self._post(routes.PROCEDURE, payload, retry=False, trace_id=trace_id)
        return QueryOut.model_validate(data)

    async def function(
        self,
        name: str,
        args: dict[str, Any] | list[Any] | None = None,
        *,
        scalar: bool = False,
        trace_id: str | None = None,
    ) -> QueryOut:
        payload = FunctionIn(
            name=name, db_schema=self._schema, args=args, scalar=scalar
        ).model_dump(mode="json", by_alias=True, exclude_none=True)
        data = await self._post(routes.FUNCTION, payload, retry=False, trace_id=trace_id)
        return QueryOut.model_validate(data)

    async def batch(
        self, items: list[BatchItem], *, mode: str = "parallel", trace_id: str | None = None
    ) -> BatchResult:
        stamped = [
            item.model_copy(
                update={"payload": {"schema": self._schema, **item.payload}}
            )
            if self._schema and "schema" not in item.payload
            else item
            for item in items
        ]
        payload = BatchRequest(mode=mode, items=stamped).model_dump(mode="json")  # type: ignore[arg-type]
        retry = mode == "parallel" and all(i.op == "view" for i in items)
        data = await self._post(routes.BATCH, payload, retry=retry, trace_id=trace_id)
        return BatchResult.model_validate(data)

    # -- lifecycle ---------------------------------------------------------

    async def ready(self) -> bool:
        try:
            response = await self._client.get(routes.READY)
        except httpx.HTTPError as exc:
            logger.warning("gateway readiness check failed: %s", exc)
            return False
        if response.status_code >= 400:
            return False
        body = _safe_json(response)
        return isinstance(body, dict) and body.get("status") != "down"

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
