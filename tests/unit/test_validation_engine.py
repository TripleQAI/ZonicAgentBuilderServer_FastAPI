"""Validation parity: every check the Django validator performed, and the
rule primitives that replaced its if/elif ladder."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.validation import rules
from app.services.validation.engine import load_rules, validate_workflow


def _agent(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "agenticWorkflowId": "11111111-2222-3333-4444-555555555555",
        "name": "wf",
        "nodes": [],
        "edges": [],
    }
    base.update(overrides)
    return base


# -- agent level ------------------------------------------------------------


def test_missing_workflow_id_is_an_error() -> None:
    result = validate_workflow({"name": "x", "nodes": [], "edges": []})
    assert result.valid is False
    assert "Missing required field: agenticWorkflowId" in result.errors


def test_empty_name_and_no_nodes_are_warnings() -> None:
    result = validate_workflow({"agenticWorkflowId": "id", "nodes": [], "edges": []})
    assert "Agent name is empty" in result.warnings
    assert "Workflow has no nodes" in result.warnings


# -- node identity ----------------------------------------------------------


def test_node_without_id_is_an_error() -> None:
    result = validate_workflow(_agent(nodes=[{"type": "note"}]))
    assert "A node is missing its id field" in result.errors


def test_duplicate_node_id_is_an_error() -> None:
    result = validate_workflow(
        _agent(nodes=[{"id": "a", "type": "note"}, {"id": "a", "type": "note"}])
    )
    assert "Duplicate node id: a" in result.errors


def test_duplicate_node_name_is_a_warning() -> None:
    result = validate_workflow(
        _agent(
            nodes=[
                {"id": "a", "type": "note", "name": "Same"},
                {"id": "b", "type": "note", "name": "Same"},
            ]
        )
    )
    assert any("Duplicate node name: Same" in w for w in result.warnings)


def test_node_without_type_is_an_error() -> None:
    result = validate_workflow(_agent(nodes=[{"id": "a", "name": "N"}]))
    assert "Node 'N' is missing its type field" in result.errors


# -- per-node rules, declared as data ---------------------------------------


@pytest.mark.parametrize("node_type", ["llm", "agent"])
def test_model_missing_warns(node_type: str) -> None:
    result = validate_workflow(
        _agent(nodes=[{"id": "a", "type": node_type, "name": "N", "config": {}}])
    )
    assert f"Node 'N' ({node_type}): model is not configured" in result.warnings


def test_sub_flow_without_child_warns() -> None:
    result = validate_workflow(
        _agent(nodes=[{"id": "a", "type": "workflow", "name": "S", "config": {}}])
    )
    assert "Sub Flow node 'S': child workflow ID is not configured" in result.warnings


def test_rule_node_without_branches_warns() -> None:
    result = validate_workflow(
        _agent(nodes=[{"id": "a", "type": "rule", "name": "R", "config": {"rules": []}}])
    )
    assert "Rule node 'R': no rule branches defined" in result.warnings


def test_rule_branch_without_rule_id_warns_once() -> None:
    result = validate_workflow(
        _agent(
            nodes=[
                {
                    "id": "a", "type": "rule", "name": "R",
                    "config": {"rules": [{"label": "x"}, {"label": "y"}]},
                }
            ]
        )
    )
    assert result.warnings.count("Rule node 'R': a branch is missing ruleId") == 1


def test_variable_update_without_path_warns() -> None:
    result = validate_workflow(
        _agent(
            nodes=[
                {
                    "id": "a", "type": "variable", "name": "V",
                    "config": {"updates": [{"value": 1}]},
                }
            ]
        )
    )
    assert "Variable node 'V': an update entry is missing variable path" in result.warnings


def test_output_without_mapping_warns() -> None:
    result = validate_workflow(
        _agent(nodes=[{"id": "a", "type": "output", "name": "O", "config": {}}])
    )
    assert "Output node 'O': no output mappings defined" in result.warnings


def test_tool_without_name_is_an_error() -> None:
    result = validate_workflow(
        _agent(nodes=[{"id": "a", "type": "tool", "name": "T", "config": {}}])
    )
    assert "Tool node 'T': toolName is required" in result.errors
    assert result.valid is False


def test_handoff_tool_without_target_warns() -> None:
    result = validate_workflow(
        _agent(
            nodes=[
                {
                    "id": "a", "type": "tool", "name": "T",
                    "config": {"toolName": "x", "toolType": "handoff"},
                }
            ]
        )
    )
    assert "Tool node 'T': handoff type requires a handoffTarget" in result.warnings


def test_non_handoff_tool_does_not_require_a_target() -> None:
    result = validate_workflow(
        _agent(
            nodes=[
                {
                    "id": "a", "type": "tool", "name": "T",
                    "config": {"toolName": "x", "toolType": "function"},
                }
            ]
        )
    )
    assert not any("handoffTarget" in w for w in result.warnings)


# -- edges ------------------------------------------------------------------


def test_dangling_edge_endpoints_warn() -> None:
    result = validate_workflow(
        _agent(
            nodes=[{"id": "a", "type": "note", "name": "A"}],
            edges=[{"id": "e", "source": "ghost", "target": "phantom"}],
        )
    )
    assert any("'ghost' not found" in w for w in result.warnings)
    assert any("'phantom' not found" in w for w in result.warnings)


def test_duplicate_edge_id_warns() -> None:
    result = validate_workflow(
        _agent(
            nodes=[{"id": "a", "type": "note", "name": "A"}],
            edges=[
                {"id": "e", "source": "a", "target": "a"},
                {"id": "e", "source": "a", "target": "a"},
            ],
        )
    )
    assert "Duplicate edge id: e" in result.warnings


def test_rule_source_handle_must_match_a_branch() -> None:
    result = validate_workflow(
        _agent(
            nodes=[
                {
                    "id": "r", "type": "rule", "name": "R",
                    "config": {"rules": [{"ruleId": "yes"}]},
                },
                {"id": "t", "type": "note", "name": "T"},
            ],
            edges=[{"id": "e", "source": "r", "target": "t", "sourceHandle": "nope"}],
        )
    )
    assert any("sourceHandle 'nope'" in w for w in result.warnings)


# -- the rule engine itself -------------------------------------------------


def test_every_declared_rule_maps_to_a_known_primitive() -> None:
    for node_type, specs in load_rules().items():
        for spec in specs:
            assert rules.get(spec["rule"]) is not None, (
                f"{node_type} declares unknown rule {spec['rule']!r}; "
                f"known: {rules.known()}"
            )


def test_every_declared_rule_has_a_message_and_severity() -> None:
    for specs in load_rules().values():
        for spec in specs:
            assert spec.get("message")
            assert spec.get("severity") in {"error", "warning"}


def test_read_path_walks_dot_paths() -> None:
    node = {"config": {"a": {"b": 7}}}
    assert rules.read_path(node, "config.a.b") == 7
    assert rules.read_path(node, "config.missing.b") is None
