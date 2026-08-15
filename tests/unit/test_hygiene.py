"""Repository hygiene rules, asserted rather than trusted (plan §14).

Two of them are security properties, not style: no SQL text in application code,
and no database credentials in this repository.
"""

from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent.parent / "app"

_SQL_KEYWORD = re.compile(
    r"\b(SELECT\s+\w|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE)\b",
    re.IGNORECASE,
)

#: Files allowed to mention SQL, and why.
_ALLOWED = {
    "test_hygiene.py",       # this file describes the rule
}


def _python_sources() -> list[Path]:
    return [p for p in APP.rglob("*.py") if p.name not in _ALLOWED]


def test_no_sql_text_in_application_code() -> None:
    """The gateway compiles all SQL; everything else is a named object."""
    offenders = []
    for path in _python_sources():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("--"):
                continue
            if _SQL_KEYWORD.search(line):
                offenders.append(f"{path.relative_to(APP)}:{lineno}: {stripped}")
    assert not offenders, "SQL found in application code:\n" + "\n".join(offenders)


def test_no_database_driver_is_imported() -> None:
    """This service has no driver. Importing one would mean a second data path."""
    banned = ("asyncpg", "psycopg", "sqlalchemy", "django")
    offenders = [
        f"{path.relative_to(APP)}: imports {name}"
        for path in _python_sources()
        for name in banned
        if re.search(rf"^\s*(import|from)\s+{name}\b", path.read_text(encoding="utf-8"), re.M)
    ]
    assert not offenders, "\n".join(offenders)


def test_no_database_credentials_in_config() -> None:
    from app.config import Settings

    fields = set(Settings.model_fields)
    for banned in ("dsn", "database_url", "db_password", "db_user", "db_host"):
        assert banned not in fields, f"Settings must not carry {banned}"


def test_only_the_gateway_package_knows_about_pgfoundation() -> None:
    """Layer direction: nothing above app/gateway may import httpx or the adapter."""
    offenders = []
    for path in _python_sources():
        relative = path.relative_to(APP)
        if relative.parts[0] == "gateway":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*import\s+httpx", text, re.M):
            offenders.append(f"{relative}: imports httpx")
        if "app.gateway.http" in text and relative.name != "main.py":
            offenders.append(f"{relative}: imports the HTTP adapter directly")
    assert not offenders, "\n".join(offenders)


def test_database_object_names_live_in_one_module() -> None:
    """No relation, view or procedure name outside domain/tables.py."""
    pattern = re.compile(r"[\"'](v_[a-z_]+|sp_[a-z_]+|fn_[a-z_]+)[\"']")
    offenders = []
    for path in _python_sources():
        relative = path.relative_to(APP)
        if relative.as_posix() == "domain/tables.py":
            continue
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            offenders.append(f"{relative}: {match.group(1)}")
    # gateway/fake.py reimplements the views by name; that is its whole job.
    offenders = [o for o in offenders if not o.startswith("gateway/fake.py")]
    assert not offenders, "database names outside domain/tables.py:\n" + "\n".join(offenders)
