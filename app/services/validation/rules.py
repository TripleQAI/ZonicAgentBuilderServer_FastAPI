"""Rule primitives — the Strategy set the validation engine dispatches to.

Five primitives cover all twelve per-node checks the Django validator performed
with a hand-written if/elif ladder (MIGRATION_PLAN.md §7.6). Seven more look
across nodes (design 7.5): a list of node IDs on one node is checked against the
nodes it names, the edges that touch them, or the same list on other nodes. None
of them names a node type, so a container type declares its rules as data.

Each primitive returns the messages it produced; the engine attaches severity.
Messages take ``{label}`` and ``{type}`` (the node being checked) and, where a
check refers to other nodes or edges, ``{ref}``, ``{refLabel}``, ``{value}`` and
``{edgeId}``.
"""

from __future__ import annotations

import operator
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuleContext:
    """The whole document, for checks that look past one node (P5-02)."""

    nodes: list[dict[str, Any]] = field(default_factory=list)
    nodes_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, Any]] = field(default_factory=list)
    edges_by_node: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    semantics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], semantics: dict[str, Any]
    ) -> RuleContext:
        nodes_by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id")}
        edges_by_node: dict[str, list[dict[str, Any]]] = {}
        for edge in edges:
            for end in {edge.get("source"), edge.get("target")}:
                if end:
                    edges_by_node.setdefault(end, []).append(edge)
        return cls(
            nodes=nodes,
            nodes_by_id=nodes_by_id,
            edges=edges,
            edges_by_node=edges_by_node,
            semantics=semantics,
        )


Rule = Callable[[dict[str, Any], dict[str, Any], str, RuleContext], list[str]]

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


def _label(node: dict[str, Any] | None, fallback: str = "") -> str:
    if not node:
        return f"'{fallback}'"
    return f"'{node.get('name') or node.get('id') or fallback}'"


def _render(template: str, node: dict[str, Any], **extra: Any) -> str:
    return template.format_map(
        _Placeholders(label=_label(node), type=node.get("type", ""), **extra)
    )


class _Placeholders(dict):  # type: ignore[type-arg]
    """Leaves a placeholder a check does not supply as written, instead of failing."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _ids(node: dict[str, Any], path: str) -> list[str]:
    value = read_path(node, path)
    return [v for v in value if isinstance(v, str) and v] if isinstance(value, list) else []


# -- one node --------------------------------------------------------------------


@rule("required")
def _required(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    value = read_path(node, spec["path"])
    return [] if value else [_render(template, node)]


@rule("non_empty_list")
def _non_empty_list(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    value = read_path(node, spec["path"]) or []
    return [] if (isinstance(value, list) and value) else [_render(template, node)]


@rule("each_item_requires")
def _each_item_requires(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    items = read_path(node, spec["path"]) or []
    if not isinstance(items, list):
        return []
    item_field = spec["field"]
    messages = [
        _render(template, node)
        for item in items
        if not (isinstance(item, dict) and item.get(item_field))
    ]
    # `once` collapses repeats, matching validators that report per node.
    return messages[:1] if (spec.get("once") and messages) else messages


@rule("required_when")
def _required_when(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    if read_path(node, spec["when"]) != spec.get("equals"):
        return []
    return [] if read_path(node, spec["path"]) else [_render(template, node)]


@rule("forbidden")
def _forbidden(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    return [_render(template, node)] if read_path(node, spec["path"]) else []


# -- across nodes (design 7.5) ---------------------------------------------------


def _allowed_types(spec: dict[str, Any], node: dict[str, Any], ctx: RuleContext) -> set[str] | None:
    """``allowedTypes``, or the list a semantics entry names, e.g. ``swarms.memberTypes``
    read from ``semantics["swarms"][node type]["memberTypes"]``."""
    if "allowedTypes" in spec:
        return set(spec["allowedTypes"])
    source = spec.get("allowedTypesFrom")
    if not source:
        return None
    section, key = source.split(".", 1)
    entry = (ctx.semantics.get(section) or {}).get(node.get("type", "")) or {}
    return set(entry.get(key) or [])


@rule("refs_exist")
def _refs_exist(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """Every ID in the list names an existing node of an allowed type."""
    allowed = _allowed_types(spec, node, ctx)
    messages = []
    for ref in _ids(node, spec["path"]):
        target = ctx.nodes_by_id.get(ref)
        if target is None or (allowed is not None and target.get("type") not in allowed):
            messages.append(_render(template, node, ref=ref, refLabel=_label(target, ref)))
    return messages


@rule("unique_by")
def _unique_by(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """The nodes the list names have distinct values at ``field``."""
    seen: set[Any] = set()
    reported: set[Any] = set()
    messages = []
    for ref in _ids(node, spec["path"]):
        target = ctx.nodes_by_id.get(ref)
        value = read_path(target, spec["field"]) if target else None
        if value in (None, ""):
            continue
        if value in seen and value not in reported:
            reported.add(value)
            messages.append(_render(template, node, value=value))
        seen.add(value)
    return messages


@rule("one_of_refs")
def _one_of_refs(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """The value is empty or one of the IDs in the list at ``refsPath``."""
    value = read_path(node, spec["path"])
    if value in (None, ""):
        return []
    return (
        []
        if value in _ids(node, spec["refsPath"])
        else [_render(template, node, ref=value, value=value)]
    )


@rule("exclusive_refs")
def _exclusive_refs(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """No ID in the list is also in the same list on an earlier node, so each
    shared ID is reported once, by the node that claims it second."""
    earlier: set[str] = set()
    for other in ctx.nodes:
        if other is node:
            break
        earlier.update(_ids(other, spec["path"]))
    return [
        _render(template, node, ref=ref, refLabel=_label(ctx.nodes_by_id.get(ref), ref))
        for ref in _ids(node, spec["path"])
        if ref in earlier
    ]


@rule("no_edges_to_refs")
def _no_edges_to_refs(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """No edge starts or ends at a node the list names."""
    messages = []
    for ref in _ids(node, spec["path"]):
        for edge in ctx.edges_by_node.get(ref, []):
            messages.append(
                _render(
                    template,
                    node,
                    ref=ref,
                    refLabel=_label(ctx.nodes_by_id.get(ref), ref),
                    edgeId=edge.get("id", ""),
                )
            )
    return messages


@rule("each_ref")
def _each_ref(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """Runs the nested ``check`` (any kind) on every node the list names (Composite)."""
    nested = spec["check"]
    primitive = get(nested["rule"])
    if primitive is None:
        raise ValueError(f"unknown validation rule {nested['rule']!r}")
    messages = []
    for ref in _ids(node, spec["path"]):
        target = ctx.nodes_by_id.get(ref)
        if target is not None and primitive(nested, target, "x", ctx):
            messages.append(_render(template, node, ref=ref, refLabel=_label(target, ref)))
    return messages


_COUNT = re.compile(r"^count\((.+)\)$")

_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
}


def _operand(node: dict[str, Any], term: Any) -> Any:
    """A number, a dot-path on the node, or ``count(path)`` (the length of a list)."""
    if not isinstance(term, str):
        return term
    match = _COUNT.match(term)
    if match:
        value = read_path(node, match.group(1))
        return len(value) if isinstance(value, list) else 0
    return read_path(node, term)


def _holds(node: dict[str, Any], left: Any, op: str, right: Any) -> bool | None:
    """The comparison, or None when a value is missing (nothing to compare)."""
    value = _operand(node, left)
    if op == "between":
        low, high = (_operand(node, bound) for bound in right)
        if not all(isinstance(v, (int, float)) for v in (value, low, high)):
            return None
        return low <= value <= high
    other = _operand(node, right)
    if not isinstance(value, (int, float)) or not isinstance(other, (int, float)):
        return None
    return _OPERATORS[op](value, other)


@rule("compare")
def _compare(
    spec: dict[str, Any], node: dict[str, Any], template: str, ctx: RuleContext
) -> list[str]:
    """``left op right`` must hold, optionally only ``when`` another comparison does.
    ``left`` may be a list of terms; each must hold, and one message is reported."""
    when = spec.get("when")
    if when and not _holds(node, when["left"], when["op"], when["right"]):
        return []
    terms = spec["left"] if isinstance(spec["left"], list) else [spec["left"]]
    failed = any(_holds(node, term, spec["op"], spec["right"]) is False for term in terms)
    return [_render(template, node)] if failed else []
