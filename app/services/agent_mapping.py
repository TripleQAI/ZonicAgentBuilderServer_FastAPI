"""Agent JSON (camelCase, from the browser) -> column payload (snake_case).

One table drives it, so adding a field is a one-line change and no per-field
`if key in body` chain exists anywhere (MIGRATION_PLAN.md §L2).

The payload uses the snake_case keys ``jsonb_populate_record`` expects in
``fn_agent_workflow_upsert``; keys absent from the payload keep their stored
value, which is the PATCH semantic the Django PUT had.
"""

from __future__ import annotations

import uuid
from typing import Any

#: JSON key -> column, for scalar fields.
SCALAR_FIELDS: dict[str, str] = {
    "bpc": "bpc",
    "name": "name",
    "displayName": "display_name",
    "description": "description",
    "editAs": "edit_as",
    "invocationType": "invocation_type",
    "isDisabled": "is_disabled",
    "isAvailableForMigration": "is_available_for_migration",
    "enableForAutoInvoke": "enable_for_auto_invoke",
    "includeThoughts": "include_thoughts",
    "appId": "app_id",
    "moduleId": "module_id",
    "environment": "environment",
    "semanticSearchEnabled": "semantic_search_enabled",
    "semanticDomain": "semantic_domain",
    "semanticKeywords": "semantic_keywords",
    "semanticUseCases": "semantic_use_cases",
}

#: JSON key -> column, for the first-class JSON fields.
JSON_FIELDS: dict[str, str] = {
    "nodes": "nodes",
    "edges": "edges",
    "variables": "variables",
    "interface": "interface",
    "skills": "skills",
    "publishChannels": "publish_channels",
    "security": "security",
}

_BOOL_COLUMNS = {
    "is_disabled", "is_available_for_migration", "enable_for_auto_invoke",
    "include_thoughts", "semantic_search_enabled", "is_root",
}


def _coerce(column: str, value: Any) -> Any:
    if column in _BOOL_COLUMNS:
        return bool(value)
    if value is None:
        return ""
    return value


def to_columns(
    body: dict[str, Any],
    *,
    agentic_workflow_id: str,
    is_root: bool | None = None,
    parent_package_id: str | None = None,
    replace_raw_json: bool = False,
) -> dict[str, Any]:
    """Build the procedure payload for one agent.

    ``replace_raw_json`` picks the merge strategy the procedure applies:

    * ``True``  (import) — ``raw_json`` is replaced wholesale, as
      ``agent_importer._save_agent`` did.
    * ``False`` (save)  — ``raw_json_patch`` is merged onto the stored value and
      the first-class fields are re-overlaid, as the Django PUT did.
    """
    columns: dict[str, Any] = {"agentic_workflow_id": str(agentic_workflow_id)}

    for json_key, column in SCALAR_FIELDS.items():
        if json_key in body:
            columns[column] = _coerce(column, body[json_key])

    for json_key, column in JSON_FIELDS.items():
        if json_key in body:
            columns[column] = body[json_key]

    if "version" in body:
        columns["version_label"] = str(body.get("version") or "")

    if is_root is not None:
        columns["is_root"] = bool(is_root)
    if parent_package_id is not None:
        columns["parent_package_id"] = str(parent_package_id)

    if replace_raw_json:
        columns["raw_json"] = body
    else:
        columns["raw_json_patch"] = body

    return columns


def ensure_workflow_id(agent_json: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Generate and write back a missing agenticWorkflowId, as the importer did."""
    workflow_id = agent_json.get("agenticWorkflowId")
    if workflow_id:
        return agent_json, str(workflow_id)
    generated = str(uuid.uuid4())
    patched = dict(agent_json)
    patched["agenticWorkflowId"] = generated
    return patched, generated
