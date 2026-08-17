"""Load the node-type registry from JSON resources.

Resolves ``{"$ref": "<fragment id>"}`` markers against ``resources/fragments``.
The output is deep-equal to the source project's ``NODE_REGISTRY`` dict, which
is the P2 exit criterion; ``tests/unit/test_registry_loader.py`` asserts the
structure and ``scripts/gen_registry_resources.py --check`` proves the
transcription still matches.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
NODE_TYPES_DIR = RESOURCES / "node_types"
FRAGMENTS_DIR = RESOURCES / "fragments"
TOOLS_FILE = RESOURCES / "tools" / "seed_tools.json"
OPTION_SETS_FILE = RESOURCES / "option_sets.json"
NODE_SEMANTICS_FILE = RESOURCES / "node_semantics.json"
MCP_CONFIG_FILE = RESOURCES / "mcp_config.json"

_MAX_DEPTH = 16


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _without_docs(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop the ``_comment`` / ``_doc`` keys the resource files carry."""
    return {k: v for k, v in payload.items() if not k.startswith("_")}


def _load_fragments() -> dict[str, Any]:
    if not FRAGMENTS_DIR.exists():
        return {}
    return {path.stem: _read(path) for path in sorted(FRAGMENTS_DIR.glob("*.json"))}


def _resolve(node: Any, fragments: dict[str, Any], depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise ValueError("fragment resolution exceeded maximum depth — reference cycle?")
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and len(node) == 1:
            if ref not in fragments:
                raise KeyError(f"unknown fragment reference: {ref!r}")
            return _resolve(fragments[ref], fragments, depth + 1)
        return {k: _resolve(v, fragments, depth + 1) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(v, fragments, depth + 1) for v in node]
    return node


@lru_cache(maxsize=1)
def load_node_registry() -> dict[str, dict[str, Any]]:
    """``{node_type: definition}``, fragments inlined, ordered by ``sortOrder``."""
    fragments = _load_fragments()
    registry: dict[str, dict[str, Any]] = {}
    for path in sorted(NODE_TYPES_DIR.glob("*.json")):
        definition = _resolve(_read(path), fragments)
        node_type = definition.get("type") or path.stem
        if node_type in registry:
            raise ValueError(f"duplicate node type {node_type!r} in {path}")
        registry[node_type] = definition
    return dict(
        sorted(registry.items(), key=lambda kv: (kv[1].get("sortOrder", 0), kv[0]))
    )


@lru_cache(maxsize=1)
def load_option_sets() -> dict[str, list[dict[str, str]]]:
    """Shared `<select>` option lists, served to the UI so it holds none itself."""
    if not OPTION_SETS_FILE.exists():  # pragma: no cover - resource is committed
        return {}
    return _without_docs(_read(OPTION_SETS_FILE))


@lru_cache(maxsize=1)
def load_mcp_config_schema() -> dict[str, Any]:
    """The MCP tool configurator, as a form schema.

    The source drew this surface from 1,347 lines of jQuery with the fields,
    option lists, conditionals and validation rules written out per tool kind.
    Serving it as data means the UI renders whatever is declared here.
    """
    if not MCP_CONFIG_FILE.exists():  # pragma: no cover - resource is committed
        return {}
    return _without_docs(_read(MCP_CONFIG_FILE))


@lru_cache(maxsize=1)
def load_node_semantics() -> dict[str, Any]:
    """Which node types reference children, hand off, or fan out into branches."""
    if not NODE_SEMANTICS_FILE.exists():  # pragma: no cover - resource is committed
        return {}
    return {
        section: _without_docs(entries) if isinstance(entries, dict) else entries
        for section, entries in _without_docs(_read(NODE_SEMANTICS_FILE)).items()
    }


@lru_cache(maxsize=1)
def load_seed_tools() -> list[dict[str, Any]]:
    if not TOOLS_FILE.exists():
        return []
    tools = _read(TOOLS_FILE)
    return list(tools) if isinstance(tools, list) else []


def to_db_rows() -> list[dict[str, Any]]:
    """Registry -> ``node_type_definition`` column shape, for the seeder.

    Mirrors the Django management command's mapping, including its
    ``formSections`` fallback and the ``validationRules`` wrapper.
    """
    rows = []
    for node_type, d in load_node_registry().items():
        rows.append(
            {
                "type": node_type,
                "label": d.get("label", node_type),
                "icon": d.get("icon", ""),
                "color": d.get("color", ""),
                "description": d.get("description", ""),
                "default_name_prefix": d.get("defaultNamePrefix", ""),
                "default_config": d.get("defaultConfig", {}),
                "handles": d.get("handles", {}),
                "form_schema": d.get("formSchema", {"sections": d.get("formSections", [])}),
                "output_schema": d.get("outputSchema", {}),
                "validation_schema": {"rules": d.get("validationRules", [])},
                "sort_order": d.get("sortOrder", 0),
            }
        )
    return rows


def to_api_rows() -> list[dict[str, Any]]:
    """Registry -> the ``/node-types`` response shape (the in-memory fallback)."""
    return [
        {
            "type": node_type,
            "label": d.get("label", node_type),
            "icon": d.get("icon", ""),
            "color": d.get("color", ""),
            "description": d.get("description", ""),
            "defaultNamePrefix": d.get("defaultNamePrefix", ""),
            "defaultConfig": d.get("defaultConfig", {}),
            "handles": d.get("handles", {}),
            "formSchema": d.get("formSchema", {"sections": d.get("formSections", [])}),
            "outputSchema": d.get("outputSchema", {}),
            "validationSchema": {"rules": d.get("validationRules", [])},
            "sortOrder": d.get("sortOrder", 0),
        }
        for node_type, d in load_node_registry().items()
    ]
