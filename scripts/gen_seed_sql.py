"""Generate db/005_seed_node_types.sql and db/006_seed_tools.sql.

The seed data exists once, as JSON under ``app/resources``. This emits the
equivalent SQL so a pure-psql environment can bootstrap without Python, while
the runtime seeder reads the same JSON (MIGRATION_PLAN.md §8.13).

    python scripts/gen_seed_sql.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.registry.loader import load_seed_tools, to_db_rows  # noqa: E402

HEADER = """\
-- {filename}
--
-- GENERATED FILE — do not edit.
-- Regenerate with:  python scripts/gen_seed_sql.py
-- Source of truth:  {source}
--
-- Idempotent: re-running updates existing rows in place.

"""


def sql_literal(value: Any) -> str:
    """A single-quoted SQL literal. Only ever called with generated data."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    return "'" + str(value).replace("'", "''") + "'"


def build_node_types_sql() -> str:
    columns = [
        "type", "label", "icon", "color", "description", "default_name_prefix",
        "default_config", "handles", "form_schema", "output_schema",
        "validation_schema", "sort_order",
    ]
    lines = [HEADER.format(
        filename="005_seed_node_types.sql", source="app/resources/node_types/*.json")]
    for row in to_db_rows():
        values = ", ".join(sql_literal(row[c]) for c in columns)
        updates = ",\n    ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "type")
        lines.append(
            f"INSERT INTO node_type_definition ({', '.join(columns)}, is_active)\n"
            f"VALUES ({values}, true)\n"
            f"ON CONFLICT (type) DO UPDATE SET\n    {updates},\n    is_active = true;\n"
        )
    lines.append(
        "INSERT INTO schema_migrations (version) VALUES ('005_seed_node_types')\n"
        "    ON CONFLICT (version) DO UPDATE SET applied_at = now();\n"
    )
    return "\n".join(lines)


def build_tools_sql() -> str:
    columns = ["name", "title", "description", "tool_type", "schema", "default_config"]
    lines = [HEADER.format(
        filename="006_seed_tools.sql", source="app/resources/tools/seed_tools.json")]
    for tool in load_seed_tools():
        values = ", ".join(sql_literal(tool.get(c)) for c in columns)
        updates = ",\n    ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "name")
        lines.append(
            f"INSERT INTO tool_definition ({', '.join(columns)}, is_active)\n"
            f"VALUES ({values}, true)\n"
            f"ON CONFLICT (name) DO UPDATE SET\n    {updates},\n    is_active = true;\n"
        )
    lines.append(
        "INSERT INTO schema_migrations (version) VALUES ('006_seed_tools')\n"
        "    ON CONFLICT (version) DO UPDATE SET applied_at = now();\n"
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    targets = {
        REPO / "db" / "005_seed_node_types.sql": build_node_types_sql(),
        REPO / "db" / "006_seed_tools.sql": build_tools_sql(),
    }

    if args.check:
        stale = [
            path.name for path, content in targets.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print("seed SQL is out of date: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("seed SQL matches the JSON resources")
        return 0

    for path, content in targets.items():
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
