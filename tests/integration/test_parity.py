"""The 14 ported Django test cases (MIGRATION_PLAN.md §12.1).

Numbering matches the source suite in ``agentBuilder/tests.py`` so the mapping
is auditable. These run against FakeGateway; the live suite re-runs the same
scenarios against the real gateway and the real procedures.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from app.registry.loader import load_node_registry

REQUIRED_NODE_TYPES = [
    "start", "llm", "agent", "rule", "workflow", "variable", "output",
    "script", "http_request", "human_input", "tool", "note", "view",
    "db_query", "approval", "guardrail", "external_agent",
]


def _small_agent(**overrides: Any) -> dict[str, Any]:
    base = {
        "agenticWorkflowId": str(uuid.uuid4()),
        "name": "root-agent",
        "displayName": "Root Agent",
        "nodes": [
            {"id": "n1", "type": "start", "name": "Start", "config": {}},
            {"id": "n2", "type": "llm", "name": "LLM", "config": {"model": "m"}},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }
    base.update(overrides)
    return base


def _child(workflow_id: str, name: str = "child") -> dict[str, Any]:
    return {
        "agenticWorkflowId": workflow_id,
        "name": name,
        "displayName": name.title(),
        "nodes": [{"id": "c1", "type": "start", "name": "Start", "config": {}}],
        "edges": [],
    }


def _sub_flow_node(node_id: str, child_id: str, name: str = "Sub Flow") -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "workflow",
        "name": name,
        "config": {"agenticWorkflowId": child_id},
    }


async def _import(client: AsyncClient, root: dict, subs: list[dict] | None = None) -> dict:
    response = await client.post(
        "/api/v1/agents/import-package",
        json={"agent_data": root, "sub_agents_data": subs},
    )
    assert response.status_code == 201, response.text
    return response.json()


# -- 1 ----------------------------------------------------------------------


def test_1_node_registry_contains_required_types() -> None:
    registry = load_node_registry()
    for node_type in REQUIRED_NODE_TYPES:
        assert node_type in registry, f"missing node type {node_type}"
    assert len(registry) == 17


# -- 2, 3 -------------------------------------------------------------------


async def test_2_import_creates_root_agent(client: AsyncClient) -> None:
    root = _small_agent()
    result = await _import(client, root)
    assert result["root_agent_id"] == root["agenticWorkflowId"]

    listing = await client.get("/api/v1/agents")
    ids = [a["agenticWorkflowId"] for a in listing.json()["agents"]]
    assert root["agenticWorkflowId"] in ids


async def test_3_import_creates_child_rows(client: AsyncClient) -> None:
    child_id = str(uuid.uuid4())
    root = _small_agent()
    root["nodes"].append(_sub_flow_node("w1", child_id))

    result = await _import(client, root, [_child(child_id)])

    assert result["sub_agent_ids"] == [child_id]
    listing = await client.get("/api/v1/agents")
    ids = {a["agenticWorkflowId"] for a in listing.json()["agents"]}
    assert {root["agenticWorkflowId"], child_id} <= ids


# -- 4, 5 -------------------------------------------------------------------


async def test_4_import_saves_root_nodes(client: AsyncClient) -> None:
    root = _small_agent()
    await _import(client, root)
    detail = (await client.get(f"/api/v1/agents/{root['agenticWorkflowId']}")).json()
    assert [n["id"] for n in detail["nodes"]] == ["n1", "n2"]


async def test_5_import_saves_root_edges(client: AsyncClient) -> None:
    root = _small_agent()
    await _import(client, root)
    detail = (await client.get(f"/api/v1/agents/{root['agenticWorkflowId']}")).json()
    assert [e["id"] for e in detail["edges"]] == ["e1"]


# -- 6 ----------------------------------------------------------------------


async def test_6_import_saves_child_nodes_and_edges(client: AsyncClient) -> None:
    child_id = str(uuid.uuid4())
    child = _child(child_id)
    child["edges"] = [{"id": "ce1", "source": "c1", "target": "c1"}]
    root = _small_agent()
    root["nodes"].append(_sub_flow_node("w1", child_id))

    await _import(client, root, [child])

    detail = (await client.get(f"/api/v1/agents/{child_id}")).json()
    assert [n["id"] for n in detail["nodes"]] == ["c1"]
    assert [e["id"] for e in detail["edges"]] == ["ce1"]


# -- 7, 8 -------------------------------------------------------------------


async def test_7_resolved_relationship_links_child(client: AsyncClient) -> None:
    child_id = str(uuid.uuid4())
    root = _small_agent()
    root["nodes"].append(_sub_flow_node("w1", child_id, "Go To Child"))

    await _import(client, root, [_child(child_id)])

    rel_map = (
        await client.get(f"/api/v1/agents/{root['agenticWorkflowId']}/relationships")
    ).json()
    assert rel_map["resolvedCount"] == 1
    assert rel_map["unresolvedCount"] == 0
    entry = rel_map["resolved"][0]
    assert entry["sourceNodeId"] == "w1"
    assert entry["sourceNodeName"] == "Go To Child"
    assert entry["childAgent"]["agenticWorkflowId"] == child_id
    assert entry["childAgent"]["nodeCount"] == 1


async def test_8_missing_child_creates_unresolved_with_warning(client: AsyncClient) -> None:
    missing_id = str(uuid.uuid4())
    root = _small_agent()
    root["nodes"].append(_sub_flow_node("w1", missing_id, "Dangling"))

    result = await _import(client, root)

    assert any(missing_id in w for w in result["warnings"])
    rel_map = (
        await client.get(f"/api/v1/agents/{root['agenticWorkflowId']}/relationships")
    ).json()
    assert rel_map["unresolvedCount"] == 1
    assert rel_map["unresolved"][0]["validationMessage"]


# -- 9, 10, 11 --------------------------------------------------------------


async def test_9_validator_detects_bad_edge_source(client: AsyncClient) -> None:
    agent = _small_agent()
    agent["edges"] = [{"id": "bad", "source": "nope", "target": "n2"}]
    result = (await client.post("/api/v1/workflows/validate", json=agent)).json()
    assert any("'nope' not found" in w for w in result["warnings"])


async def test_10_validator_detects_duplicate_node_ids(client: AsyncClient) -> None:
    agent = _small_agent()
    agent["nodes"].append({"id": "n1", "type": "note", "name": "Dupe", "config": {}})
    result = (await client.post("/api/v1/workflows/validate", json=agent)).json()
    assert result["valid"] is False
    assert "Duplicate node id: n1" in result["errors"]


async def test_11_valid_workflow_returns_valid_true(client: AsyncClient) -> None:
    result = (await client.post("/api/v1/workflows/validate", json=_small_agent())).json()
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["node_count"] == 2
    assert result["edge_count"] == 1


# -- 12, 13 -----------------------------------------------------------------


async def test_12_export_package_returns_agent_and_sub_agents(client: AsyncClient) -> None:
    child_id = str(uuid.uuid4())
    root = _small_agent()
    root["nodes"].append(_sub_flow_node("w1", child_id))
    await _import(client, root, [_child(child_id)])

    package = (
        await client.get(
            f"/api/v1/agents/{root['agenticWorkflowId']}/export-package"
        )
    ).json()

    assert package["agent"]["agenticWorkflowId"] == root["agenticWorkflowId"]
    assert len(package["sub_agents"]) == 1
    assert package["sub_agents"][0]["agenticWorkflowId"] == child_id
    assert package["relationshipMap"][0]["childAgenticWorkflowId"] == child_id


async def test_13_export_uses_current_nodes_not_stale_raw_json(client: AsyncClient) -> None:
    root = _small_agent()
    await _import(client, root)
    workflow_id = root["agenticWorkflowId"]

    # Save a different node set; raw_json still carries the imported one.
    await client.put(
        f"/api/v1/agents/{workflow_id}",
        json={"nodes": [{"id": "fresh", "type": "note", "name": "Fresh", "config": {}}]},
    )

    exported = (await client.get(f"/api/v1/agents/{workflow_id}/export")).json()
    assert [n["id"] for n in exported["nodes"]] == ["fresh"]


# -- 14 ---------------------------------------------------------------------


async def test_14_save_load_preserves_extra_raw_json_keys(client: AsyncClient) -> None:
    root = _small_agent(originalBpc="BPC-1", freezeRelease=True)
    await _import(client, root)
    workflow_id = root["agenticWorkflowId"]

    await client.put(
        f"/api/v1/agents/{workflow_id}",
        json={"displayName": "Renamed", "nodes": root["nodes"], "edges": root["edges"]},
    )

    detail = (await client.get(f"/api/v1/agents/{workflow_id}")).json()
    assert detail["originalBpc"] == "BPC-1"
    assert detail["freezeRelease"] is True
    assert detail["displayName"] == "Renamed"

    exported = (await client.get(f"/api/v1/agents/{workflow_id}/export")).json()
    assert exported["originalBpc"] == "BPC-1"


# -- the real package -------------------------------------------------------


@pytest.mark.parametrize("with_subs", [True, False])
async def test_real_package_round_trips(
    client: AsyncClient,
    agent_json: dict[str, Any],
    sub_agents_json: list[dict[str, Any]],
    with_subs: bool,
) -> None:
    """The 28-node / 54-edge sample package from the source project."""
    subs = sub_agents_json if with_subs else None
    result = await _import(client, agent_json, subs)

    workflow_id = agent_json["agenticWorkflowId"]
    assert result["root_agent_id"] == workflow_id
    assert result["relationship_count"] == 9  # nine Sub Flow nodes

    exported = (await client.get(f"/api/v1/agents/{workflow_id}/export")).json()
    assert len(exported["nodes"]) == len(agent_json["nodes"])
    assert len(exported["edges"]) == len(agent_json["edges"])
    # Keys the model does not know about must survive.
    for key in ("createdBy", "createdOn", "freezeRelease"):
        assert exported[key] == agent_json[key]
