"""Every governed call must name the agent_builder schema.

The views and procedures live in `agent_builder`, not `public`, and this service
does not control the gateway connection's search_path. If the schema stopped
being sent, every read would fail with "relation does not exist" at runtime —
so it is pinned here instead.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.domain import tables
from app.gateway.http import HttpPgGateway
from app.gateway.models import BatchItem

DB_DIR = Path(__file__).resolve().parent.parent.parent / "db"


def _capture() -> tuple[HttpPgGateway, list[dict[str, Any]]]:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.read()))
        # Each route has its own envelope; return the one it expects.
        if request.url.path.endswith("/batch"):
            return httpx.Response(
                200,
                json={"mode": "parallel", "elapsed_ms": 0.0, "ok_count": 0,
                      "error_count": 0, "results": []},
            )
        return httpx.Response(200, json={"rows": [], "row_count": 0, "elapsed_ms": 0.0})

    settings = Settings(pg_gateway_schema="agent_builder", pg_gateway_max_retries=0)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw")
    return HttpPgGateway(settings, client=client), seen


async def test_view_sends_the_schema() -> None:
    gateway, seen = _capture()
    await gateway.view("v_agent_summary")
    assert seen[0]["schema"] == "agent_builder"
    assert seen[0]["name"] == "v_agent_summary"


async def test_procedure_sends_the_schema_and_keeps_null_placeholders() -> None:
    gateway, seen = _capture()
    await gateway.procedure("sp_agent_workflow_save", ["{}", "[]", "fmt", None, None, None])
    assert seen[0]["schema"] == "agent_builder"
    assert seen[0]["args"][-3:] == [None, None, None]


async def test_batch_items_inherit_the_schema() -> None:
    gateway, seen = _capture()
    await gateway.batch(
        [BatchItem(id="a", datasource="agentbuilder", op="view",
                   payload={"name": "v_agent_summary"})]
    )
    assert seen[0]["items"][0]["payload"]["schema"] == "agent_builder"


async def test_an_empty_schema_setting_sends_nothing() -> None:
    """An unqualified deployment must not send `"schema": null`."""
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.read()))
        return httpx.Response(200, json={"rows": [], "row_count": 0})

    settings = Settings(pg_gateway_schema="", pg_gateway_max_retries=0)
    gateway = HttpPgGateway(
        settings,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw"),
    )
    await gateway.view("v_agent_summary")
    assert "schema" not in seen[0]


# -- the SQL and the specs must agree on the object names -------------------


def _sql_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(DB_DIR.glob("*.sql"))
        if path.name != "999_drop_all.sql"
    )


@pytest.mark.parametrize(
    "relation",
    [spec.relation for spec in vars(tables).values() if isinstance(spec, tables.RelationSpec)],
)
def test_every_relation_spec_has_a_view_in_the_sql(relation: str) -> None:
    assert f"CREATE OR REPLACE VIEW agent_builder.{relation}" in _sql_text(), (
        f"{relation} is declared in domain/tables.py but not created in db/"
    )


@pytest.mark.parametrize(
    "procedure",
    [spec.name for spec in vars(tables).values() if isinstance(spec, tables.ProcedureSpec)],
)
def test_every_procedure_spec_exists_in_the_sql(procedure: str) -> None:
    assert f"CREATE OR REPLACE PROCEDURE agent_builder.{procedure}" in _sql_text(), (
        f"{procedure} is declared in domain/tables.py but not created in db/"
    )


def test_django_table_names_stay_quoted_in_every_script() -> None:
    """Mixed-case identifiers fold to lower case unquoted, so an unquoted
    reference would silently point at a table that does not exist.

    Two spellings are legitimate: `"agentBuilder_x"` as an identifier, and
    `'agentBuilder_x'` as a string literal — 005 looks the names up in
    information_schema, where they are data rather than identifiers.
    """
    offenders = []
    for path in sorted(DB_DIR.glob("*.sql")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            for index in _find_all(line, "agentBuilder_"):
                if index == 0 or line[index - 1] not in ('"', "'"):
                    offenders.append(f"{path.name}:{lineno}: {stripped}")
                    break
    assert not offenders, "unquoted Django table name:\n" + "\n".join(offenders)


def _find_all(haystack: str, needle: str) -> list[int]:
    positions, start = [], haystack.find(needle)
    while start != -1:
        positions.append(start)
        start = haystack.find(needle, start + 1)
    return positions
