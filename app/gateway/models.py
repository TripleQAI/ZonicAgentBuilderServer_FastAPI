"""Mirrors of the pgfoundation v1 wire contract.

These match the DTOs in ``ZonicPostgresqlServer_FastAPI`` — ``ViewIn``,
``ProcedureIn``, ``BatchRequest``, ``QueryOut``, ``BatchResult``. They are
declared here rather than imported so this project has no build-time dependency
on that repository; ``tests/contract`` pins them against its committed OpenAPI
snapshot (MIGRATION_PLAN.md §12.4).

Field names are snake_case because that is the gateway's wire format. This is
the only module in the project that speaks it.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FilterOp(StrEnum):
    """The gateway's closed operator whitelist. Nothing outside this exists."""

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    ILIKE = "ilike"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class Filter(BaseModel):
    column: str
    op: FilterOp = FilterOp.EQ
    value: Any = None


class OrderBy(BaseModel):
    column: str
    descending: bool = False


class SchemaQualified(BaseModel):
    """Base for the name-based payloads.

    The wire field is ``schema``; it is ``db_schema`` here because ``schema``
    shadows a Pydantic member — the same accommodation the gateway makes, and
    part of its contract. Dump these models with ``by_alias=True``.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    db_schema: str | None = Field(default=None, alias="schema")


class ViewIn(SchemaQualified):
    """Governed read of a named view or table."""

    columns: list[str] | None = None
    filters: list[Filter] = Field(default_factory=list)
    order_by: list[OrderBy] = Field(default_factory=list)
    limit: int | None = None
    offset: int | None = None


class ProcedureIn(SchemaQualified):
    """``CALL name(args...)``. NULL placeholders stand in for INOUT parameters."""

    args: list[Any] | None = None


class FunctionIn(SchemaQualified):
    args: dict[str, Any] | list[Any] | None = None
    scalar: bool = False


class BatchItem(BaseModel):
    id: str
    datasource: str
    op: str
    payload: dict[str, Any] = Field(default_factory=dict)


class BatchRequest(BaseModel):
    mode: Literal["parallel", "sequential", "transactional"] | None = None
    items: list[BatchItem] = Field(default_factory=list)


class QueryOut(BaseModel):
    """The gateway read envelope. ``columns`` appears only in tuple row format."""

    rows: list[dict[str, Any] | list[Any]] = Field(default_factory=list)
    row_count: int = 0
    elapsed_ms: float = 0.0
    columns: list[str] | None = None

    def dict_rows(self) -> list[dict[str, Any]]:
        """Rows as mappings. We always request the default dict row format."""
        return [row for row in self.rows if isinstance(row, dict)]

    def first(self) -> dict[str, Any] | None:
        rows = self.dict_rows()
        return rows[0] if rows else None


class BatchItemResult(BaseModel):
    id: str
    status: Literal["ok", "error"]
    rows: list[dict[str, Any]] | None = None
    row_count: int | None = None
    elapsed_ms: float | None = None
    error: dict[str, Any] | None = None


class BatchResult(BaseModel):
    mode: str
    elapsed_ms: float = 0.0
    ok_count: int = 0
    error_count: int = 0
    results: list[BatchItemResult] = Field(default_factory=list)
