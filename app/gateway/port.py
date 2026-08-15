"""The data-access port.

Everything above ``app/gateway`` depends on this Protocol, not on pgfoundation.
Two adapters implement it: :class:`~app.gateway.http.HttpPgGateway` for real
use and :class:`~app.gateway.fake.FakeGateway` for the unit-test suite, which
therefore needs no network and no database (MIGRATION_PLAN.md §5, §12.1).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.gateway.models import BatchItem, BatchResult, Filter, OrderBy, QueryOut


@runtime_checkable
class PgGateway(Protocol):
    """Four operations. Nothing above this layer needs a fifth."""

    async def view(
        self,
        name: str,
        *,
        columns: list[str] | None = None,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> QueryOut:
        """Governed read of a named view."""
        ...

    async def procedure(self, name: str, args: list[Any] | None = None) -> QueryOut:
        """``CALL`` a named procedure. One call, one transaction."""
        ...

    async def function(
        self, name: str, args: dict[str, Any] | list[Any] | None = None, *, scalar: bool = False
    ) -> QueryOut:
        """Invoke a named function."""
        ...

    async def batch(
        self, items: list[BatchItem], *, mode: str = "parallel"
    ) -> BatchResult:
        """Run several operations in one round trip."""
        ...

    async def ready(self) -> bool:
        """True when the data path is usable."""
        ...

    async def aclose(self) -> None:
        """Release any transport resources."""
        ...
