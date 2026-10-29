"""Derive parent -> child relationships from a canvas, and shape the map.

This is the business logic the plan keeps in Python (MIGRATION_PLAN.md §8.5):
walking nodes to find Sub Flow children and Agent handoff targets. The
procedures only persist what this module produces.

Ported from ``agentBuilder/services/relationship_resolver.py``, with its
``if node_type == 'workflow' / elif node_type == 'agent'`` chain replaced by a
lookup into ``resources/node_semantics.json``. A new node type that references a
child is a JSON edit, not a new branch here.

Two derivation modes exist because the Django app resolved differently in each
path, and parity requires reproducing both:

* **save** — a Sub Flow child is resolved against the database, so the SQL
  ``resolve`` flag is set and the join decides.
* **import** — a Sub Flow child is resolved against the package being imported,
  so Python decides and passes the verdict through.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.domain.schemas.agent import (
    ChildAgentRef,
    RelationshipEntry,
    RelationshipMap,
    UnreferencedAgent,
)
from app.registry.loader import load_node_semantics

_AGENT_INFO_KEYS = ("agentId", "agentName", "agentVersion")
#: A handoff row points at a node of the same workflow, not at a child workflow.
_HANDOFF = "handoff"


def _child_reference_paths() -> dict[str, str]:
    return load_node_semantics().get("childReference", {})


def _handoff_paths() -> dict[str, str]:
    return load_node_semantics().get("handoffTargets", {})


def _read_path(node: dict[str, Any], dot_path: str) -> Any:
    current: Any = node
    for part in dot_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _as_uuid(value: Any) -> str | None:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def _sub_keys(config: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: config[k] for k in keys if k in config}


def _handoff_rows(node: dict[str, Any], parent_wf_id: str, path: str) -> list[dict[str, Any]]:
    """Handoffs point at a node inside the same workflow, so they are always
    resolved and never looked up."""
    targets = _read_path(node, path) or []
    if isinstance(targets, str):
        targets = [targets]
    return [
        {
            "child_agentic_workflow_id": parent_wf_id,
            "source_node_id": node.get("id", ""),
            "source_node_name": node.get("name", ""),
            "source_node_type": node.get("type", ""),
            "relationship_type": _HANDOFF,
            "config_inputs": {"targetNodeId": target},
            "agent_info": {},
            "app_info": {},
            "module_info": {},
            "is_resolved": True,
            "validation_message": "",
            "resolve": False,
            "link_child": False,
        }
        for target in targets
        if target
    ]


def _sub_flow_row(node: dict[str, Any], child_id: str) -> dict[str, Any]:
    config = node.get("config") or {}
    return {
        "child_agentic_workflow_id": child_id,
        "source_node_id": node.get("id", ""),
        "source_node_name": node.get("name", ""),
        "source_node_type": node.get("type", ""),
        "relationship_type": "sub_flow",
        "config_inputs": config,
        "agent_info": _sub_keys(config, _AGENT_INFO_KEYS),
        "app_info": _sub_keys(config, ("appId",)),
        "module_info": _sub_keys(config, ("moduleId",)),
        "is_resolved": False,
        "validation_message": "",
        "resolve": True,
        "link_child": True,
    }


def derive_for_save(nodes: list[dict[str, Any]], parent_wf_id: str) -> list[dict[str, Any]]:
    """Relationship rows for a PUT. Sub Flow children resolve against the DB."""
    child_paths = _child_reference_paths()
    handoff_paths = _handoff_paths()
    rows: list[dict[str, Any]] = []

    for node in nodes or []:
        node_type = node.get("type", "")

        if node_type in child_paths:
            child_id = _as_uuid(_read_path(node, child_paths[node_type]))
            if child_id is not None:
                rows.append(_sub_flow_row(node, child_id))

        if node_type in handoff_paths:
            rows.extend(_handoff_rows(node, parent_wf_id, handoff_paths[node_type]))

    return rows


def derive_for_import(
    root_nodes: list[dict[str, Any]], package_child_ids: set[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Relationship rows for an import, plus the user-visible warnings.

    Resolution is against the package, matching ``agent_importer.import_package``:
    a Sub Flow whose child is not in ``sub_agents`` is recorded unresolved even
    if a row with that id happens to already exist in the database.
    """
    child_paths = _child_reference_paths()
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for node in root_nodes or []:
        node_type = node.get("type", "")
        if node_type not in child_paths:
            continue

        raw_child_id = _read_path(node, child_paths[node_type])
        if not raw_child_id:
            continue

        child_id = _as_uuid(raw_child_id)
        if child_id is None:
            warnings.append(
                f"Node '{node.get('id', '')}' has invalid agenticWorkflowId "
                f"'{raw_child_id}' — skipped"
            )
            continue

        resolved = child_id in package_child_ids
        if not resolved:
            warnings.append(
                f"Node '{node.get('name', node.get('id', ''))}' references "
                f"agenticWorkflowId '{child_id}' which is not in sub_agents"
            )

        row = _sub_flow_row(node, child_id)
        row["resolve"] = False
        row["is_resolved"] = resolved
        row["validation_message"] = (
            "" if resolved else f"Child workflow {child_id} not found in sub_agents"
        )
        rows.append(row)

    return rows, warnings


def build_map(
    root_agentic_workflow_id: str,
    root_name: str,
    relationship_rows: list[dict[str, Any]],
    package_members: list[dict[str, Any]],
) -> RelationshipMap:
    """Shape the relationship-map response. One read produced every input."""
    resolved: list[RelationshipEntry] = []
    unresolved: list[RelationshipEntry] = []

    for row in relationship_rows:
        # Handoffs are kept for parity but have no child workflow to resolve; listing them
        # would show each one as an unresolved reference to the parent itself.
        if row.get("relationship_type") == _HANDOFF:
            continue
        entry = RelationshipEntry(
            source_node_id=row.get("source_node_id") or "",
            source_node_name=row.get("source_node_name") or "",
            child_agentic_workflow_id=str(row.get("child_agentic_workflow_id")),
            is_resolved=bool(row.get("is_resolved")),
        )
        if entry.is_resolved and row.get("child_name") is not None:
            entry.child_agent = ChildAgentRef(
                agentic_workflow_id=str(row.get("child_agentic_workflow_id")),
                name=row.get("child_name") or "",
                display_name=row.get("child_display_name") or "",
                node_count=int(row.get("child_node_count") or 0),
                edge_count=int(row.get("child_edge_count") or 0),
            )
            resolved.append(entry)
        else:
            entry.validation_message = row.get("validation_message") or ""
            unresolved.append(entry)

    referenced = {str(r.get("child_agentic_workflow_id")) for r in relationship_rows}
    unreferenced = [
        UnreferencedAgent(
            agentic_workflow_id=str(member["agentic_workflow_id"]),
            name=member.get("name") or "",
            display_name=member.get("display_name") or "",
        )
        for member in package_members
        if str(member["agentic_workflow_id"]) not in referenced
        and str(member["agentic_workflow_id"]) != root_agentic_workflow_id
    ]

    return RelationshipMap(
        root_agent_id=root_agentic_workflow_id,
        root_agent_name=root_name,
        resolved_count=len(resolved),
        unresolved_count=len(unresolved),
        resolved=resolved,
        unresolved=unresolved,
        unreferenced_sub_agents=unreferenced,
    )
