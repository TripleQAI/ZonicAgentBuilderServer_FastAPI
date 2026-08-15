"""BaseRepository — Template Method over the gateway.

Reads are derived from a :class:`RelationSpec`; writes are derived from a
:class:`ProcedureSpec`, including the NULL placeholders its INOUT parameters
need. Subclasses declare a spec and add only their bespoke reads
(MIGRATION_PLAN.md §5, §7.2).
"""

from __future__ import annotations

import json
from typing import Any

from app.domain.tables import ProcedureSpec, RelationSpec
from app.gateway.models import Filter, FilterOp, OrderBy
from app.gateway.port import PgGateway


def as_json_arg(value: Any) -> str:
    """Encode a jsonb procedure argument.

    Sent as JSON *text*: the gateway's psycopg driver registers no dict/list to
    jsonb adapter, and psycopg dumps ``str`` with an unspecified OID so the
    server coerces it into the jsonb parameter position (MIGRATION_PLAN.md
    §8.10). ``db/010_api_procedures.sql`` declares those parameters ``jsonb``.
    """
    return json.dumps(value, default=str)


class BaseRepository:
    def __init__(self, gateway: PgGateway, spec: RelationSpec | None = None) -> None:
        self._gateway = gateway
        self._spec = spec

    @property
    def spec(self) -> RelationSpec:
        if self._spec is None:  # pragma: no cover - programming error
            raise RuntimeError(f"{type(self).__name__} has no RelationSpec")
        return self._spec

    # -- reads -------------------------------------------------------------

    async def list(
        self,
        filters: list[Filter] | None = None,
        *,
        order_by: list[OrderBy] | None = None,
        limit: int | None = None,
        spec: RelationSpec | None = None,
    ) -> list[dict[str, Any]]:
        target = spec or self.spec
        result = await self._gateway.view(
            target.relation,
            columns=target.column_list(),
            filters=filters or [],
            order_by=order_by if order_by is not None else target.order_list(),
            limit=limit,
        )
        return result.dict_rows()

    async def get_by(
        self, column: str, value: Any, *, spec: RelationSpec | None = None
    ) -> dict[str, Any] | None:
        rows = await self.list([Filter(column=column, op=FilterOp.EQ, value=value)], spec=spec)
        return rows[0] if rows else None

    async def get(
        self, key_value: Any, *, spec: RelationSpec | None = None
    ) -> dict[str, Any] | None:
        target = spec or self.spec
        return await self.get_by(target.key, key_value, spec=target)

    async def list_in(
        self, column: str, values: list[Any], *, spec: RelationSpec | None = None
    ) -> list[dict[str, Any]]:
        """IN filters reject an empty list at the gateway, so short-circuit here."""
        if not values:
            return []
        return await self.list(
            [Filter(column=column, op=FilterOp.IN, value=values)], spec=spec
        )

    async def exists(self, key_value: Any) -> bool:
        return await self.get(key_value) is not None

    # -- writes ------------------------------------------------------------

    async def call(self, procedure: ProcedureSpec, *args: Any) -> dict[str, Any]:
        """Invoke a procedure, appending its INOUT NULL placeholders."""
        if len(args) != procedure.arity:
            raise ValueError(
                f"{procedure.name} takes {procedure.arity} arguments, got {len(args)}"
            )
        payload = [*args, *([None] * procedure.placeholders)]
        result = await self._gateway.procedure(procedure.name, payload)
        return result.first() or {}
