"""The Postman collection must match the API it documents.

A collection is hand-maintained, so it drifts the moment a route is added or
renamed. These tests compare it against the app's own OpenAPI document, which
means the drift shows up here rather than as a 404 in someone's Postman run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.config import Settings
from app.gateway.fake import FakeGateway
from app.main import create_app

POSTMAN = Path(__file__).parent.parent.parent / "docs" / "postman"
COLLECTION = POSTMAN / "agent-builder.postman_collection.json"
ENVIRONMENT = POSTMAN / "agent-builder.postman_environment.json"


@pytest.fixture(scope="module")
def collection() -> dict[str, Any]:
    return json.loads(COLLECTION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def openapi_paths() -> set[tuple[str, str]]:
    app = create_app(
        Settings(pg_gateway_provider="fake", embedding_provider="fake"),
        gateway=FakeGateway(),
    )
    spec = app.openapi()
    return {
        (method.upper(), path)
        for path, operations in spec["paths"].items()
        for method in operations
    }


def _requests(node: Any) -> list[dict[str, Any]]:
    """Flatten the folder tree into a list of requests."""
    out: list[dict[str, Any]] = []
    for item in node.get("item", []):
        if "request" in item:
            out.append(item)
        else:
            out.extend(_requests(item))
    return out


def _api_calls(collection: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(method, normalised path, request name) for requests against {{API}}.

    Path variables are substituted back to their OpenAPI names so the two sides
    are comparable.
    """
    calls = []
    for item in _requests(collection):
        raw = item["request"]["url"]["raw"]
        if not raw.startswith("{{API}}"):
            continue
        path = raw[len("{{API}}") :]
        path = path.replace("{{ID}}", "{agentic_workflow_id}")
        # A literal uuid in the URL stands in for the same path parameter.
        path = re.sub(r"/[0-9a-f]{8}-[0-9a-f-]{27}", "/{agentic_workflow_id}", path)
        calls.append((item["request"]["method"], path, item["name"]))
    return calls


# -- structure ---------------------------------------------------------------


def test_collection_is_valid_v2_1() -> None:
    payload = json.loads(COLLECTION.read_text(encoding="utf-8"))
    assert payload["info"]["schema"].endswith("v2.1.0/collection.json")
    assert payload["info"]["name"]
    assert payload["item"], "collection has no folders"


def test_environment_is_valid() -> None:
    payload = json.loads(ENVIRONMENT.read_text(encoding="utf-8"))
    assert payload["_postman_variable_scope"] == "environment"
    keys = {v["key"] for v in payload["values"]}
    assert {"API", "GW", "DS", "SCHEMA", "ID"} <= keys


def test_every_request_has_a_url_and_method(collection: dict[str, Any]) -> None:
    for item in _requests(collection):
        assert item["request"]["method"], f"{item['name']} has no method"
        assert item["request"]["url"]["raw"], f"{item['name']} has no URL"


def test_json_bodies_parse(collection: dict[str, Any]) -> None:
    for item in _requests(collection):
        body = item["request"].get("body")
        if body and body.get("mode") == "raw":
            try:
                json.loads(body["raw"])
            except json.JSONDecodeError as exc:
                pytest.fail(f"{item['name']} has an unparsable body: {exc}")


def test_urls_only_use_declared_variables(collection: dict[str, Any]) -> None:
    declared = {v["key"] for v in collection["variable"]}
    for item in _requests(collection):
        raw = item["request"]["url"]["raw"]
        body = (item["request"].get("body") or {}).get("raw", "")
        for name in re.findall(r"\{\{(\w+)\}\}", raw + body):
            assert name in declared, f"{item['name']} uses undeclared {{{{{name}}}}}"


# -- agreement with the API --------------------------------------------------


def test_every_collection_request_hits_a_real_route(
    collection: dict[str, Any], openapi_paths: set[tuple[str, str]]
) -> None:
    unknown = [
        f"{method} {path}  ({name})"
        for method, path, name in _api_calls(collection)
        if (method, path) not in openapi_paths
    ]
    assert not unknown, "collection points at routes the API does not serve:\n" + "\n".join(
        unknown
    )


def test_every_route_appears_in_the_collection(
    collection: dict[str, Any], openapi_paths: set[tuple[str, str]]
) -> None:
    covered = {(method, path) for method, path, _ in _api_calls(collection)}
    missing = [f"{m} {p}" for m, p in sorted(openapi_paths) if (m, p) not in covered]
    assert not missing, "API routes with no Postman request:\n" + "\n".join(missing)


def test_gateway_requests_target_the_governed_surface(
    collection: dict[str, Any],
) -> None:
    """The gateway folder must not reach for the raw-SQL endpoints, which are
    disabled by design."""
    allowed = {"view", "procedure", "function", "batch", "datasources", "ready"}
    for item in _requests(collection):
        raw = item["request"]["url"]["raw"]
        if not raw.startswith("{{GW}}"):
            continue
        tail = raw.rstrip("/").rsplit("/", 1)[-1]
        assert tail in allowed, f"{item['name']} calls the gateway's {tail!r} surface"


def test_procedure_calls_send_their_inout_placeholders(
    collection: dict[str, Any],
) -> None:
    """A CALL through the gateway needs one trailing null per INOUT parameter,
    and jsonb arguments must be JSON text rather than objects."""
    from app.domain import tables

    specs = {
        s.name: s for s in vars(tables).values() if isinstance(s, tables.ProcedureSpec)
    }

    for item in _requests(collection):
        raw = item["request"]["url"]["raw"]
        if not raw.endswith("/procedure"):
            continue
        body = json.loads(item["request"]["body"]["raw"])
        spec = specs.get(body["name"])
        assert spec, f"{item['name']} calls unknown procedure {body['name']!r}"

        args = body["args"]
        assert len(args) == spec.arity + spec.placeholders, (
            f"{item['name']}: {body['name']} takes {spec.arity} argument(s) plus "
            f"{spec.placeholders} INOUT placeholder(s), got {len(args)}"
        )
        assert args[spec.arity :] == [None] * spec.placeholders, (
            f"{item['name']}: the last {spec.placeholders} argument(s) must be null"
        )
        for value in args[: spec.arity]:
            assert not isinstance(value, (dict, list)), (
                f"{item['name']}: jsonb arguments go as JSON text, not as objects"
            )
