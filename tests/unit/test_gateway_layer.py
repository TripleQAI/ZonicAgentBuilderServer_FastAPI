"""The gateway boundary: payload construction, the ACL, and the port contract."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.config import Settings
from app.core.errors import ConflictError, DataUnavailableError, UpstreamError
from app.domain import tables
from app.gateway.errors import translate_status, translate_transport
from app.gateway.fake import FakeGateway
from app.gateway.http import HttpPgGateway
from app.gateway.models import Filter, FilterOp, OrderBy
from app.gateway.port import PgGateway
from app.repositories.base import BaseRepository, as_json_arg


def _client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://gw"
    )


def _gateway(handler: Any) -> HttpPgGateway:
    settings = Settings(pg_gateway_datasource="agentbuilder", pg_gateway_max_retries=0)
    return HttpPgGateway(settings, client=_client(handler))


# -- payload construction ---------------------------------------------------


async def test_view_posts_a_governed_payload_with_no_sql() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"rows": [], "row_count": 0, "elapsed_ms": 1.0})

    gateway = _gateway(handler)
    await gateway.view(
        "v_agent_summary",
        columns=["name"],
        filters=[Filter(column="is_root", op=FilterOp.EQ, value=True)],
        order_by=[OrderBy(column="updated_at", descending=True)],
        limit=10,
    )

    assert seen["url"] == "http://gw/v1/datasources/agentbuilder/view"
    body = seen["body"]
    assert '"name":"v_agent_summary"' in body.replace(" ", "")
    for keyword in ("SELECT", "select", "INSERT", "UPDATE", "DELETE"):
        assert keyword not in body


async def test_procedure_appends_inout_null_placeholders() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"rows": [{"o_count": 1}], "row_count": 1})

    repo = BaseRepository(_gateway(handler))
    await repo.call(tables.UPSERT_NODE_TYPES, as_json_arg([{"type": "x"}]))

    # arity 1 + placeholders 1
    assert seen["body"].replace(" ", "").endswith('null]}')


async def test_call_rejects_the_wrong_argument_count() -> None:
    repo = BaseRepository(FakeGateway())
    with pytest.raises(ValueError, match="takes 3 arguments"):
        await repo.call(tables.SAVE_AGENT, "only-one")


def test_json_arguments_are_sent_as_text() -> None:
    encoded = as_json_arg({"nodes": [{"id": "n1"}]})
    assert isinstance(encoded, str)
    assert encoded == '{"nodes": [{"id": "n1"}]}'


# -- anti-corruption layer --------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, UpstreamError),   # our malformed call, not the caller's
        (401, UpstreamError),
        (403, UpstreamError),
        (404, UpstreamError),   # unknown datasource = misconfiguration
        (409, ConflictError),
        (413, UpstreamError),
        (422, UpstreamError),
        (500, UpstreamError),
        (503, DataUnavailableError),
    ],
)
def test_gateway_status_maps_to_our_error(status: int, expected: type) -> None:
    error = translate_status(status, {"error": "boom", "type": "QueryError"})
    assert isinstance(error, expected)
    assert "boom" in error.message
    assert "QueryError" in error.message


def test_retry_after_is_forwarded() -> None:
    error = translate_status(503, {"error": "pool timeout"}, headers={"retry-after": "5"})
    assert error.headers["Retry-After"] == "5"


def test_transport_failure_is_a_data_outage() -> None:
    error = translate_transport(httpx.ConnectError("refused"))
    assert isinstance(error, DataUnavailableError)
    assert error.status_code == 503


async def test_http_gateway_raises_translated_errors() -> None:
    gateway = _gateway(
        lambda _r: httpx.Response(409, json={"error": "dup", "type": "IntegrityError"})
    )
    with pytest.raises(ConflictError):
        await gateway.view("v_agent_summary")


async def test_reads_retry_but_writes_do_not() -> None:
    attempts = {"view": 0, "procedure": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        key = "procedure" if request.url.path.endswith("procedure") else "view"
        attempts[key] += 1
        return httpx.Response(503, json={"error": "pool timeout"})

    settings = Settings(pg_gateway_max_retries=2)
    gateway = HttpPgGateway(settings, client=_client(handler))

    with pytest.raises(DataUnavailableError):
        await gateway.view("v_agent_summary")
    with pytest.raises(DataUnavailableError):
        await gateway.procedure("sp_agent_workflow_save", [None])

    assert attempts["view"] == 3      # initial + 2 retries
    assert attempts["procedure"] == 1  # a write is never retried here


# -- port conformance -------------------------------------------------------


def test_both_adapters_satisfy_the_port() -> None:
    assert isinstance(FakeGateway(), PgGateway)
    assert isinstance(_gateway(lambda _r: httpx.Response(200, json={})), PgGateway)


# -- the fake's filter semantics --------------------------------------------


@pytest.mark.parametrize(
    ("op", "value", "expected"),
    [
        (FilterOp.EQ, "a", ["a"]),
        (FilterOp.NE, "a", ["b", "c"]),
        (FilterOp.IN, ["a", "c"], ["a", "c"]),
        (FilterOp.NOT_IN, ["a"], ["b", "c"]),
        (FilterOp.ILIKE, "A", ["a"]),
    ],
)
async def test_fake_filters(op: FilterOp, value: Any, expected: list[str]) -> None:
    gateway = FakeGateway()
    gateway.tool_definition = [{"name": n, "is_active": True} for n in ("a", "b", "c")]
    result = await gateway.view(
        "v_tool_active", filters=[Filter(column="name", op=op, value=value)]
    )
    assert [r["name"] for r in result.dict_rows()] == expected
