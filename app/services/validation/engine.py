"""Workflow validation.

Graph-level checks (identity, duplicates, dangling edges, rule handles) live
here because they are properties of the whole canvas. Per-node checks are data,
declared in ``resources/validation_rules.json`` and dispatched through the
primitives in :mod:`app.services.validation.rules`.

Ported from ``agentBuilder/services/workflow_validator.py``. Message text,
severity and emission order are identical, so the validation modal renders the
same content as the source.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.schemas.workflow import ValidationResult
from app.services.validation import rules as rule_primitives

RULES_FILE = Path(__file__).resolve().parent.parent.parent / "resources" / "validation_rules.json"


@lru_cache(maxsize=1)
def load_rules() -> dict[str, list[dict[str, Any]]]:
    if not RULES_FILE.exists():  # pragma: no cover - resource is committed
        return {}
    raw = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _apply_node_rules(
    node: dict[str, Any], errors: list[str], warnings: list[str]
) -> None:
    for spec in load_rules().get(node.get("type", ""), []):
        primitive = rule_primitives.get(spec["rule"])
        if primitive is None:  # pragma: no cover - guarded by a unit test
            raise ValueError(f"unknown validation rule {spec['rule']!r}")
        bucket = errors if spec.get("severity") == "error" else warnings
        bucket.extend(primitive(spec, node, spec["message"]))


def validate_workflow(agent_json: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    # -- agent level -------------------------------------------------------
    if not agent_json.get("agenticWorkflowId"):
        errors.append("Missing required field: agenticWorkflowId")
    if not agent_json.get("name"):
        warnings.append("Agent name is empty")

    nodes = agent_json.get("nodes") or []
    edges = agent_json.get("edges") or []

    if not nodes:
        warnings.append("Workflow has no nodes")

    # -- nodes -------------------------------------------------------------
    node_ids: set[str] = set()
    node_names: dict[str, str] = {}

    for node in nodes:
        node_id = node.get("id")
        node_name = node.get("name", "")
        node_type = node.get("type", "")
        label = f"'{node_name or node_id}'"

        if not node_id:
            errors.append("A node is missing its id field")
            continue
        if node_id in node_ids:
            errors.append(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)

        if node_name:
            if node_name in node_names:
                warnings.append(
                    f"Duplicate node name: {node_name} "
                    f"(ids: {node_names[node_name]} and {node_id})"
                )
            node_names[node_name] = node_id

        if not node_type:
            errors.append(f"Node {label} is missing its type field")
            continue

        _apply_node_rules(node, errors, warnings)

    # -- rule handles, for edge validation ---------------------------------
    rule_handles: dict[str, set[str]] = {}
    for node in nodes:
        if node.get("type") == "rule" and node.get("id"):
            branches = (node.get("config") or {}).get("rules") or []
            rule_handles[node["id"]] = {
                b["ruleId"] for b in branches if isinstance(b, dict) and b.get("ruleId")
            }

    # -- edges -------------------------------------------------------------
    seen_edge_ids: set[str] = set()

    for edge in edges:
        edge_id = edge.get("id", "")
        source = edge.get("source")
        target = edge.get("target")
        source_handle = edge.get("sourceHandle")

        if edge_id:
            if edge_id in seen_edge_ids:
                warnings.append(f"Duplicate edge id: {edge_id}")
            seen_edge_ids.add(edge_id)

        if source and source not in node_ids:
            warnings.append(f"Edge {edge_id!r}: source node {source!r} not found in nodes")
        if target and target not in node_ids:
            warnings.append(f"Edge {edge_id!r}: target node {target!r} not found in nodes")

        if source and source in rule_handles:
            valid = rule_handles[source]
            if source_handle and valid and source_handle not in valid:
                warnings.append(
                    f"Edge {edge_id!r}: sourceHandle {source_handle!r} "
                    f"not found in Rule node {source!r} rule IDs"
                )

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        node_count=len(nodes),
        edge_count=len(edges),
    )
