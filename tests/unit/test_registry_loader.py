"""The registry must load, resolve fragments, and keep its shape."""

from __future__ import annotations

import pytest

from app.registry import loader

EXPECTED_TYPES = {
    "start", "llm", "agent", "external_agent", "script", "http_request",
    "guardrail", "rule", "workflow", "variable", "output", "approval",
    "human_input", "tool", "note", "view", "db_query", "swarm",
}


def test_all_eighteen_node_types_load() -> None:
    assert set(loader.load_node_registry()) == EXPECTED_TYPES


def test_registry_is_ordered_by_sort_order() -> None:
    orders = [d.get("sortOrder", 0) for d in loader.load_node_registry().values()]
    assert orders == sorted(orders)


def test_fragments_are_inlined_not_left_as_refs() -> None:
    def has_ref(node: object) -> bool:
        if isinstance(node, dict):
            return "$ref" in node or any(has_ref(v) for v in node.values())
        if isinstance(node, list):
            return any(has_ref(v) for v in node)
        return False

    assert not has_ref(loader.load_node_registry())


def test_shared_sections_are_present_where_the_source_had_them() -> None:
    registry = loader.load_node_registry()
    llm_sections = registry["llm"]["formSchema"]["sections"]
    titles = [s.get("title") or s.get("label") for s in llm_sections]
    assert "Output Structure" in titles
    assert "Variable Updates" in titles


def test_model_options_fragment_resolved() -> None:
    llm = loader.load_node_registry()["llm"]
    definition = llm["formSchema"]["sections"][0]["fields"][0]
    assert definition["key"] == "config.model"
    assert {o["value"] for o in definition["options"]} == {
        "claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5",
        "nemotron-3-ultra", "nemotron-3-super", "nemotron-3-nano", "nemotron-3.5-super-vl",
    }


def test_db_rows_match_the_django_seed_command_shape() -> None:
    rows = loader.to_db_rows()
    assert len(rows) == 18
    row = next(r for r in rows if r["type"] == "rule")
    assert set(row) == {
        "type", "label", "icon", "color", "description", "default_name_prefix",
        "default_config", "handles", "form_schema", "output_schema",
        "validation_schema", "sort_order",
    }
    assert "rules" in row["validation_schema"]


def test_api_rows_use_camel_case_keys() -> None:
    row = loader.to_api_rows()[0]
    assert "defaultNamePrefix" in row
    assert "formSchema" in row
    assert "validationSchema" in row


def test_unknown_fragment_reference_is_an_error() -> None:
    with pytest.raises(KeyError):
        loader._resolve({"$ref": "does.not.exist"}, {})


def test_reference_cycle_is_detected() -> None:
    fragments = {"a": {"$ref": "b"}, "b": {"$ref": "a"}}
    with pytest.raises(ValueError, match="cycle"):
        loader._resolve({"$ref": "a"}, fragments)
