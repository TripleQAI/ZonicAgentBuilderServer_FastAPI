"""CamelModel — the browser-facing wire format, declared once.

Every response model inherits this, so the camelCase JSON the existing frontend
expects is produced by the alias generator instead of by hand-written dicts
(MIGRATION_PLAN.md §L2).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.core.naming import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        ser_json_timedelta="iso8601",
    )
