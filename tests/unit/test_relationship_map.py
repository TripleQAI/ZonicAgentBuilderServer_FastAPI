"""The relationship map lists child workflows: Sub Flow references, resolved or not. Agent
handoffs are derived and stored too, but they point at nodes of the same workflow."""

from __future__ import annotations

from typing import Any

from app.services.relationship_service import build_map, derive_for_save

ROOT = "11111111-2222-3333-4444-555555555555"
CHILD = "66666666-7777-8888-9999-000000000000"


def _rows_as_stored(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What the relationships view returns after a save: the derived rows, with the child's
    summary joined in for a Sub Flow whose child exists."""
    rows = derive_for_save(nodes, ROOT)
    for row in rows:
        if row["relationship_type"] != "handoff" and row["child_agentic_workflow_id"] == CHILD:
            row |= {"is_resolved": True, "child_name": "child", "child_display_name": "Child"}
    return rows


def test_handoffs_are_not_listed_as_unresolved_children() -> None:
    nodes = [
        {
            "id": "sup",
            "name": "supervisor",
            "type": "agent",
            "config": {"handoffTarget": ["flow", "llm"]},
        },
        {
            "id": "flow",
            "name": "child_flow",
            "type": "workflow",
            "config": {"agenticWorkflowId": CHILD},
        },
        {"id": "llm", "name": "general", "type": "llm", "config": {}},
    ]
    rows = _rows_as_stored(nodes)
    assert {r["relationship_type"] for r in rows} == {"handoff", "sub_flow"}  # both still stored

    rel_map = build_map(ROOT, "root", rows, [])

    assert rel_map.unresolved_count == 0 and rel_map.unresolved == []
    assert [(e.source_node_id, e.child_agentic_workflow_id) for e in rel_map.resolved] == [
        ("flow", CHILD)
    ]
