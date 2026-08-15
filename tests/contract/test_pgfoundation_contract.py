"""Pin our gateway client against pgfoundation's committed OpenAPI snapshot.

If that service renames a route or a DTO, this fails with a diff instead of
production failing with a 422 (MIGRATION_PLAN.md §12.4).

The snapshot is vendored into this repo so CI never depends on the reference
checkout being present. Refresh it with:

    cp <pgfoundation>/tests/contract/openapi.v1.snapshot.json \\
       tests/contract/pgfoundation.openapi.v1.snapshot.json
"""

from __future__ import annotations

import json
from pathlib import Path

from app.gateway import routes
from app.gateway.models import BatchRequest, ProcedureIn, QueryOut, ViewIn

SNAPSHOT = Path(__file__).parent / "pgfoundation.openapi.v1.snapshot.json"


def _snapshot() -> dict[str, dict[str, str | None]]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_every_route_we_call_exists_in_the_snapshot() -> None:
    snapshot = _snapshot()
    expected = {
        f"POST {routes.VIEW.format(datasource='{name}')}": "ViewIn",
        f"POST {routes.PROCEDURE.format(datasource='{name}')}": "ProcedureIn",
        f"POST {routes.BATCH}": "BatchRequest",
    }
    for key, request_model in expected.items():
        assert key in snapshot, f"{key} is not in the pgfoundation contract"
        assert snapshot[key]["request"] == request_model


def test_readiness_probe_exists_and_is_unversioned() -> None:
    assert f"GET {routes.READY}" in _snapshot()


def test_read_responses_use_the_query_envelope() -> None:
    snapshot = _snapshot()
    assert snapshot[f"POST {routes.VIEW.format(datasource='{name}')}"]["response"] == "QueryOut"
    assert (
        snapshot[f"POST {routes.PROCEDURE.format(datasource='{name}')}"]["response"]
        == "QueryOut"
    )


def test_our_dtos_serialise_to_the_documented_field_names() -> None:
    """Dumped the way the adapter dumps them: by_alias, so `db_schema` goes out
    as `schema` — the gateway's documented field name (its doc 08 §8.2)."""
    view = ViewIn(name="v_agent_summary", db_schema="agent_builder").model_dump(
        by_alias=True, exclude_none=True
    )
    assert set(view) <= {
        "name", "schema", "columns", "filters", "order_by", "limit", "offset"
    }
    assert view["schema"] == "agent_builder"
    assert "db_schema" not in view

    procedure = ProcedureIn(
        name="sp_x", db_schema="agent_builder", args=[None]
    ).model_dump(by_alias=True, exclude_none=True)
    assert set(procedure) == {"name", "schema", "args"}
    # INOUT placeholders are None *inside* args and must survive exclude_none.
    assert procedure["args"] == [None]

    batch = BatchRequest(mode="parallel").model_dump()
    assert set(batch) == {"mode", "items"}


def test_query_envelope_parses_both_row_formats() -> None:
    dict_rows = QueryOut.model_validate(
        {"rows": [{"a": 1}], "row_count": 1, "elapsed_ms": 0.4}
    )
    assert dict_rows.dict_rows() == [{"a": 1}]

    tuple_rows = QueryOut.model_validate(
        {"rows": [[1, 2]], "row_count": 1, "elapsed_ms": 0.4, "columns": ["a", "b"]}
    )
    # We always request dict format; tuple rows must not crash the parser.
    assert tuple_rows.dict_rows() == []


def test_we_never_reference_the_raw_sql_surface() -> None:
    """query/execute are trusted_only and stay disabled. Nothing may call them."""
    module_paths = [routes.VIEW, routes.PROCEDURE, routes.FUNCTION, routes.BATCH, routes.READY]
    assert not any(p.endswith(("/query", "/execute", "/execute-many")) for p in module_paths)
