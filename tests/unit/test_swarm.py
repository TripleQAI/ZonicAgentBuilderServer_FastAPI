"""Swarm nodes: a container whose members are agent or LLM nodes. The registry
serves its container layout, and validation checks the cross-node rules (SW-*)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.services.validation.engine import validate_workflow


def _agent(*nodes: dict[str, Any], edges: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "agenticWorkflowId": "11111111-2222-3333-4444-555555555555",
        "name": "team",
        "nodes": list(nodes),
        "edges": edges or [],
    }


def _member(node_id: str, name: str, node_type: str = "agent") -> dict[str, Any]:
    config: dict[str, Any] = {"model": "gpt-5-mini", "systemPrompt": f"You are {name}."}
    if node_type == "llm":
        config = {
            "model": "gpt-5-mini",
            "messages": [{"role": "system", "content": f"You are {name}."}],
        }
    return {
        "id": node_id,
        "type": node_type,
        "name": name,
        "parentId": "swarm_1",
        "position": {"x": 24, "y": 72},
        "config": config,
    }


def _swarm(members: list[str], entry: str = "") -> dict[str, Any]:
    return {
        "id": "swarm_1",
        "type": "swarm",
        "name": "team",
        "position": {"x": 300, "y": 0},
        "config": {
            "members": members,
            "entryPoint": entry,
            "taskMapping": "{{system.userQuery}}",
            "maxHandoffs": 10,
            "maxIterations": 15,
            "executionTimeoutSeconds": 600,
            "nodeTimeoutSeconds": 120,
            "repetitiveHandoffDetectionWindow": 6,
            "repetitiveHandoffMinUniqueAgents": 2,
        },
    }


def _mentions(messages: list[str], text: str) -> bool:
    return any(text in message for message in messages)


async def test_the_registry_serves_the_swarm_as_a_container(client: AsyncClient) -> None:
    response = await client.get("/api/v1/node-types")
    assert response.status_code == 200, response.text
    swarm = next(t for t in response.json()["nodeTypes"] if t["type"] == "swarm")
    assert swarm["layout"]["kind"] == "container"
    assert swarm["layout"]["minWidth"] > 0
    semantics = (await client.get("/api/v1/node-semantics")).json()
    assert semantics["swarms"]["swarm"]["membersPath"] == "config.members"


def test_a_swarm_of_two_members_is_valid() -> None:
    result = validate_workflow(
        _agent(
            _swarm(["a", "w"], entry="a"), _member("a", "planner"), _member("w", "writer", "llm")
        )
    )
    assert not [e for e in result.errors if "swarm" in e.lower() or "member" in e.lower()], (
        result.errors
    )


def test_a_swarm_without_members_is_an_error() -> None:
    assert _mentions(validate_workflow(_agent(_swarm([]))).errors, "team")


def test_an_edge_to_a_member_is_an_error() -> None:
    edge = {
        "id": "e1",
        "source": "start_1",
        "target": "a",
        "sourceHandle": "default",
        "targetHandle": "default",
    }
    start = {
        "id": "start_1",
        "type": "start",
        "name": "Start_1",
        "position": {"x": 0, "y": 0},
        "config": {},
    }
    result = validate_workflow(
        _agent(
            start,
            _swarm(["a", "w"], entry="a"),
            _member("a", "planner"),
            _member("w", "writer"),
            edges=[edge],
        )
    )
    assert _mentions(result.errors, "Edge e1 connects to swarm member")


def test_an_entry_point_outside_the_members_is_an_error() -> None:
    result = validate_workflow(
        _agent(_swarm(["a", "w"], entry="x"), _member("a", "planner"), _member("w", "writer"))
    )
    assert result.valid is False
