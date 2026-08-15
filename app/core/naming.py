"""snake_case <-> camelCase. The wire is camelCase; the database is snake_case.

Used by the Pydantic alias generator and by the row mapper, so the conversion
exists once instead of in every hand-written dict (MIGRATION_PLAN.md §L2).
"""

from __future__ import annotations

import re

_SNAKE_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def to_camel(value: str) -> str:
    """``display_name`` -> ``displayName``. Leading underscores are preserved."""
    head, *rest = value.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


def to_snake(value: str) -> str:
    """``displayName`` -> ``display_name``."""
    return _SNAKE_BOUNDARY.sub("_", value).lower()
