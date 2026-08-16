"""Requirement 2 of the brief — "low code, do not write hard coded code" —
asserted rather than trusted.

Each of these caught something real when it was written.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from app.registry.loader import (
    load_node_registry,
    load_node_semantics,
    load_option_sets,
)
from app.services.validation.engine import load_rules

APP = Path(__file__).resolve().parent.parent.parent / "app"
RESOURCES = APP / "resources"
UI_SRC = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "ZonicAgentBuilderUI_NextJS"
    / "src"
)


def _service_sources() -> list[Path]:
    """Business logic only. Resource loaders and the fake gateway legitimately
    name things the services must not."""
    return [
        p
        for p in (APP / "services").rglob("*.py")
        if p.name != "__init__.py"
    ]


# -- node types are data, not literals --------------------------------------


def test_services_do_not_branch_on_node_type_literals() -> None:
    """`if node_type == "workflow"` belongs in node_semantics.json.

    Walks the AST rather than the text, so a docstring that *describes* the old
    if-chain does not register as one.
    """
    known = set(load_node_registry())
    offenders = []

    for path in _service_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            operands = [node.left, *node.comparators]
            for operand in operands:
                if (
                    isinstance(operand, ast.Constant)
                    and isinstance(operand.value, str)
                    and operand.value in known
                ):
                    offenders.append(
                        f"{path.name}:{operand.lineno}: compares against {operand.value!r}"
                    )

    assert not offenders, (
        "node type compared as a literal — declare it in node_semantics.json:\n"
        + "\n".join(offenders)
    )


def test_node_semantics_only_reference_real_node_types() -> None:
    known = set(load_node_registry())
    semantics = load_node_semantics()
    for section, entries in semantics.items():
        for node_type in entries:
            assert node_type in known, (
                f"node_semantics.{section} names {node_type!r}, which is not a node type"
            )


def test_validation_rules_only_reference_real_node_types() -> None:
    known = set(load_node_registry())
    for node_type in load_rules():
        assert node_type in known, f"validation_rules.json names unknown type {node_type!r}"


# -- option lists are served, not duplicated --------------------------------


REQUIRED_OPTION_SETS = [
    "mappingTypes",
    "stateOps",
    "schemaTypes",
    "messageRoles",
    "invocationTypes",
    "semanticDomains",
]


@pytest.mark.parametrize("name", REQUIRED_OPTION_SETS)
def test_option_set_is_published(name: str) -> None:
    options = load_option_sets().get(name)
    assert options, f"{name} is missing from option_sets.json"
    for option in options:
        assert set(option) == {"value", "label"}


def test_ui_declares_no_option_lists_of_its_own() -> None:
    """The UI must read option lists from /option-sets, not carry its own.

    Skipped when the UI is not checked out beside this project.
    """
    if not UI_SRC.exists():
        pytest.skip("frontend not present")

    served = {
        option["value"]
        for options in load_option_sets().values()
        for option in options
    }
    literal = re.compile(r"value:\s*'([^']+)'")
    offenders = []
    for path in UI_SRC.rglob("*.tsx"):
        if path.name.endswith(".test.tsx"):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in literal.finditer(line):
                if match.group(1) in served:
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "option value hard-coded in the UI — read it from useOptions():\n"
        + "\n".join(offenders)
    )


# -- resource files stay well-formed ----------------------------------------


@pytest.mark.parametrize(
    "resource", ["option_sets.json", "node_semantics.json", "validation_rules.json"]
)
def test_resource_parses_and_documents_itself(resource: str) -> None:
    payload = json.loads((RESOURCES / resource).read_text(encoding="utf-8"))
    assert "_comment" in payload, f"{resource} should say what it is for"
    assert len(payload) > 1, f"{resource} is empty apart from its comment"


# -- the two declarations of "where handoffs live" must agree ----------------


def test_handoff_path_matches_the_registry_field() -> None:
    """`node_semantics.handoffTargets` and the registry must point at the same
    place.

    The UI finds the handoff list by looking for the field its handoff editor
    is bound to (`node_multiselect`); the backend reads node_semantics.json to
    derive relationships. Two declarations of one fact, so they are checked
    against each other rather than trusted.
    """
    registry = load_node_registry()
    declared = load_node_semantics().get("handoffTargets", {})

    from_registry: dict[str, str] = {}
    for node_type, definition in registry.items():
        for section in definition.get("formSchema", {}).get("sections", []):
            for field in section.get("fields", []):
                if field.get("type") == "node_multiselect":
                    from_registry[node_type] = field["key"]

    assert from_registry == declared, (
        "node_semantics.handoffTargets disagrees with the registry.\n"
        f"  registry (node_multiselect fields): {from_registry}\n"
        f"  node_semantics.json:                {declared}"
    )
