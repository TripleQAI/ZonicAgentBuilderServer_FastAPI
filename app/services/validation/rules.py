"""Rule primitives — the Strategy set the validation engine dispatches to.

Five primitives cover all twelve per-node checks the Django validator performed
with a hand-written if/elif ladder (MIGRATION_PLAN.md §7.6).

Each primitive returns the messages it produced; the engine attaches severity.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Rule = Callable[[dict[str, Any], dict[str, Any], str], list[str]]

_REGISTRY: dict[str, Rule] = {}


def rule(name: str) -> Callable[[Rule], Rule]:
    def decorate(fn: Rule) -> Rule:
        _REGISTRY[name] = fn
        return fn

    return decorate


def get(name: str) -> Rule | None:
    return _REGISTRY.get(name)


def known() -> list[str]:
    return sorted(_REGISTRY)


def read_path(node: dict[str, Any], dot_path: str) -> Any:
    """Resolve a dot-path against a node, the same convention the forms use."""
    current: Any = node
    for part in dot_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _render(template: str, node: dict[str, Any]) -> str:
    label = node.get("name") or node.get("id") or ""
    return template.format(label=f"'{label}'", type=node.get("type", ""))


@rule("required")
def _required(spec: dict[str, Any], node: dict[str, Any], template: str) -> list[str]:
    value = read_path(node, spec["path"])
    return [] if value else [_render(template, node)]


@rule("non_empty_list")
def _non_empty_list(spec: dict[str, Any], node: dict[str, Any], template: str) -> list[str]:
    value = read_path(node, spec["path"]) or []
    return [] if (isinstance(value, list) and value) else [_render(template, node)]


@rule("each_item_requires")
def _each_item_requires(
    spec: dict[str, Any], node: dict[str, Any], template: str
) -> list[str]:
    items = read_path(node, spec["path"]) or []
    if not isinstance(items, list):
        return []
    field = spec["field"]
    messages = [
        _render(template, node)
        for item in items
        if not (isinstance(item, dict) and item.get(field))
    ]
    # `once` collapses repeats, matching validators that report per node.
    return messages[:1] if (spec.get("once") and messages) else messages


@rule("required_when")
def _required_when(spec: dict[str, Any], node: dict[str, Any], template: str) -> list[str]:
    if read_path(node, spec["when"]) != spec.get("equals"):
        return []
    return [] if read_path(node, spec["path"]) else [_render(template, node)]


@rule("forbidden")
def _forbidden(spec: dict[str, Any], node: dict[str, Any], template: str) -> list[str]:
    return [_render(template, node)] if read_path(node, spec["path"]) else []
