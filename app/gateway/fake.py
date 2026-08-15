"""In-memory implementation of the data path, for tests.

Backs the entire unit suite so it runs with no database and no gateway. It
implements the same relations and procedures as ``db/009_api_views.sql`` and
``db/010_api_procedures.sql``.

This is a second implementation of the same semantics, so it can drift from the
SQL. That risk is covered by the live integration suite, which runs the same
test cases against the real gateway and the real procedures
(MIGRATION_PLAN.md §12.4).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.errors import NotFoundError
from app.gateway.models import (
    BatchItem,
    BatchItemResult,
    BatchResult,
    Filter,
    FilterOp,
    OrderBy,
    QueryOut,
)

_AGENT_DEFAULTS: dict[str, Any] = {
    "bpc": "", "name": "", "display_name": "", "description": "", "edit_as": "",
    "invocation_type": "", "is_disabled": False, "is_available_for_migration": False,
    "enable_for_auto_invoke": False, "include_thoughts": False, "app_id": "",
    "module_id": "", "environment": "", "version_label": "", "is_root": False,
    "parent_package_id": None, "nodes": [], "edges": [], "variables": {},
    "interface": {}, "skills": [], "publish_channels": [], "security": {},
    "raw_json": {}, "semantic_search_enabled": False, "semantic_domain": "",
    "semantic_keywords": "", "semantic_use_cases": "", "embedding_vector": None,
    "embedding_text": "", "embedding_updated_at": None,
}


def _count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _now() -> str:
    return datetime.now(UTC).isoformat()


class FakeGateway:
    """Implements :class:`~app.gateway.port.PgGateway` against dicts."""

    def __init__(self) -> None:
        self.agent_workflow: list[dict[str, Any]] = []
        self.agent_relationship: list[dict[str, Any]] = []
        self.agent_workflow_chip: list[dict[str, Any]] = []
        self.workflow_snapshot: list[dict[str, Any]] = []
        self.node_type_definition: list[dict[str, Any]] = []
        self.tool_definition: list[dict[str, Any]] = []
        self.calls: list[tuple[str, Any]] = []

    # -- view --------------------------------------------------------------

    async def view(
        self,
        name: str,
        *,
        columns: list[str] | None = None,
        filters: list[Filter] | None = None,
        order_by: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        trace_id: str | None = None,
    ) -> QueryOut:
        # Relations are keyed by bare name here; the schema is a deployment
        # detail the real gateway resolves.
        self.calls.append(("view", name))
        rows = self._relation(name)
        for f in filters or []:
            rows = [r for r in rows if _matches(r.get(f.column), f)]
        for ob in reversed(order_by or []):
            rows = sorted(
                rows, key=lambda r: (r.get(ob.column) is None, r.get(ob.column)),
                reverse=ob.descending,
            )
        if offset:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        if columns:
            rows = [{c: r.get(c) for c in columns} for r in rows]
        return QueryOut(rows=list(rows), row_count=len(rows), elapsed_ms=0.0)

    def _relation(self, name: str) -> list[dict[str, Any]]:
        builder = getattr(self, f"_view_{name}", None)
        if builder is not None:
            return list(builder())
        table = getattr(self, name, None)
        if table is None:
            raise NotFoundError(f"unknown relation {name!r}")
        return list(table)

    # -- views (mirroring db/009_api_views.sql) ----------------------------

    def _view_v_agent_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "agentic_workflow_id": a["agentic_workflow_id"],
                "name": a["name"],
                "display_name": a["display_name"],
                "is_root": a["is_root"],
                "environment": a["environment"],
                "updated_at": a["updated_at"],
                "node_count": _count(a["nodes"]),
                "edge_count": _count(a["edges"]),
            }
            for a in self.agent_workflow
        ]

    def _view_v_agent_detail(self) -> list[dict[str, Any]]:
        rows = []
        for a in self.agent_workflow:
            detail = dict(a["raw_json"])
            detail.update(
                {
                    "agenticWorkflowId": a["agentic_workflow_id"],
                    "nodes": a["nodes"], "edges": a["edges"],
                    "variables": a["variables"], "interface": a["interface"],
                    "skills": a["skills"], "publishChannels": a["publish_channels"],
                    "security": a["security"],
                    "semanticSearchEnabled": a["semantic_search_enabled"],
                    "semanticDomain": a["semantic_domain"],
                    "semanticKeywords": a["semantic_keywords"],
                    "semanticUseCases": a["semantic_use_cases"],
                }
            )
            rows.append(
                {
                    "agentic_workflow_id": a["agentic_workflow_id"],
                    "name": a["name"], "display_name": a["display_name"],
                    "description": a["description"], "bpc": a["bpc"],
                    "is_root": a["is_root"],
                    "parent_package_id": a["parent_package_id"],
                    "semantic_search_enabled": a["semantic_search_enabled"],
                    "updated_at": a["updated_at"],
                    "detail_json": detail,
                }
            )
        return rows

    def _view_v_agent_export(self) -> list[dict[str, Any]]:
        rows = []
        for a in self.agent_workflow:
            export = dict(a["raw_json"])
            export.update(
                {
                    "nodes": a["nodes"], "edges": a["edges"],
                    "variables": a["variables"], "interface": a["interface"],
                    "skills": a["skills"], "publishChannels": a["publish_channels"],
                    "security": a["security"],
                }
            )
            rows.append(
                {
                    "agentic_workflow_id": a["agentic_workflow_id"],
                    "parent_package_id": a["parent_package_id"],
                    "is_root": a["is_root"],
                    "export_json": export,
                }
            )
        return rows

    def _view_v_agent_relationship_detail(self) -> list[dict[str, Any]]:
        by_id = {a["id"]: a for a in self.agent_workflow}
        rows = []
        for r in self.agent_relationship:
            child = by_id.get(r["child_agent_id"]) if r["child_agent_id"] else None
            rows.append(
                {
                    **{k: r[k] for k in (
                        "id", "parent_agentic_workflow_id", "child_agentic_workflow_id",
                        "source_node_id", "source_node_name", "source_node_type",
                        "relationship_type", "config_inputs", "is_resolved",
                        "validation_message",
                    )},
                    "child_name": child["name"] if child else None,
                    "child_display_name": child["display_name"] if child else None,
                    "child_node_count": _count(child["nodes"]) if child else 0,
                    "child_edge_count": _count(child["edges"]) if child else 0,
                }
            )
        return rows

    def _view_v_package_agent(self) -> list[dict[str, Any]]:
        return [
            {
                "parent_package_id": a["parent_package_id"],
                "agentic_workflow_id": a["agentic_workflow_id"],
                "name": a["name"], "display_name": a["display_name"],
                "is_root": a["is_root"],
            }
            for a in self.agent_workflow
            if a["parent_package_id"] is not None
        ]

    def _view_v_node_type_active(self) -> list[dict[str, Any]]:
        return [n for n in self.node_type_definition if n.get("is_active", True)]

    def _view_v_tool_active(self) -> list[dict[str, Any]]:
        return [t for t in self.tool_definition if t.get("is_active", True)]

    def _view_v_schema_migration(self) -> list[dict[str, Any]]:
        return [{"version": "fake", "applied_at": _now(), "checksum": ""}]

    # -- procedures (mirroring db/010_api_procedures.sql) ------------------

    async def procedure(
        self, name: str, args: list[Any] | None = None, *, trace_id: str | None = None
    ) -> QueryOut:
        self.calls.append(("procedure", name))
        handler = getattr(self, f"_proc_{name}", None)
        if handler is None:
            raise NotFoundError(f"unknown procedure {name!r}")
        row = handler(*(args or []))
        return QueryOut(rows=[row], row_count=1, elapsed_ms=0.0)

    def _upsert_agent(self, agent: dict[str, Any]) -> dict[str, Any]:
        wf_id = str(agent["agentic_workflow_id"])
        existing = next(
            (a for a in self.agent_workflow if a["agentic_workflow_id"] == wf_id), None
        )
        if existing is None:
            existing = {
                "id": str(uuid.uuid4()),
                "agentic_workflow_id": wf_id,
                "created_at": _now(),
                **_AGENT_DEFAULTS,
            }
            self.agent_workflow.append(existing)
        # PATCH semantics: only keys present in the payload are written.
        for key, value in agent.items():
            if key in _AGENT_DEFAULTS:
                existing[key] = value

        # Mirrors the raw_json strategy selector in fn_agent_workflow_upsert.
        if "raw_json_patch" in agent:
            merged = dict(existing.get("raw_json") or {})
            merged.update(agent["raw_json_patch"] or {})
            merged.update(
                {
                    "nodes": existing["nodes"], "edges": existing["edges"],
                    "variables": existing["variables"], "interface": existing["interface"],
                    "skills": existing["skills"],
                    "publishChannels": existing["publish_channels"],
                    "security": existing["security"],
                    "semanticSearchEnabled": existing["semantic_search_enabled"],
                    "semanticDomain": existing["semantic_domain"],
                    "semanticKeywords": existing["semantic_keywords"],
                    "semanticUseCases": existing["semantic_use_cases"],
                }
            )
            existing["raw_json"] = merged

        existing["updated_at"] = _now()

        chip = next(
            (c for c in self.agent_workflow_chip if c["agentic_workflow_id"] == wf_id), None
        )
        if chip is None:
            chip = {"id": str(uuid.uuid4()), "agentic_workflow_id": wf_id}
            self.agent_workflow_chip.append(chip)
        chip.update(
            {
                "bpc": existing["bpc"], "name": existing["name"],
                "display_name": existing["display_name"],
                "description": existing["description"],
                "is_disabled": existing["is_disabled"],
            }
        )
        return existing

    def _replace_relationships(
        self, parent: dict[str, Any], relationships: list[dict[str, Any]], fmt: str
    ) -> int:
        self.agent_relationship = [
            r for r in self.agent_relationship if r["parent_agent_id"] != parent["id"]
        ]
        for rel in relationships or []:
            child_wf = str(rel["child_agentic_workflow_id"])
            resolve = bool(rel.get("resolve"))
            link_child = bool(rel.get("link_child"))
            child = next(
                (a for a in self.agent_workflow if a["agentic_workflow_id"] == child_wf), None
            )
            resolved = (child is not None) if resolve else bool(rel.get("is_resolved", False))
            self.agent_relationship.append(
                {
                    "id": str(uuid.uuid4()),
                    "parent_agent_id": parent["id"],
                    "child_agent_id": child["id"] if (link_child and resolved and child) else None,
                    "parent_agentic_workflow_id": parent["agentic_workflow_id"],
                    "child_agentic_workflow_id": child_wf,
                    "source_node_id": rel.get("source_node_id", ""),
                    "source_node_name": rel.get("source_node_name", ""),
                    "source_node_type": rel.get("source_node_type", "workflow"),
                    "relationship_type": rel.get("relationship_type", "sub_flow"),
                    "config_inputs": rel.get("config_inputs") or {},
                    "agent_info": rel.get("agent_info") or {},
                    "app_info": rel.get("app_info") or {},
                    "module_info": rel.get("module_info") or {},
                    "is_resolved": resolved,
                    "validation_message": (fmt % child_wf)
                    if (resolve and not resolved) else rel.get("validation_message", ""),
                    "created_at": _now(), "updated_at": _now(),
                }
            )
        return len(relationships or [])

    def _proc_sp_agent_workflow_save(
        self, agent: Any, relationships: Any, fmt: Any, *_placeholders: Any
    ) -> dict[str, Any]:
        agent = _as_json(agent)
        row = self._upsert_agent(agent)
        count = self._replace_relationships(
            row, _as_json(relationships) or [], fmt or "Child workflow %s not found in database"
        )
        return {
            "o_relationship_count": count,
            "o_node_count": _count(row["nodes"]),
            "o_edge_count": _count(row["edges"]),
        }

    def _proc_sp_agent_package_import(
        self, root: Any, sub_agents: Any, relationships: Any, fmt: Any, *_placeholders: Any
    ) -> dict[str, Any]:
        children = _as_json(sub_agents) or []
        for child in children:
            self._upsert_agent(child)
        root_json = _as_json(root)
        root_row = self._upsert_agent(root_json)
        count = self._replace_relationships(
            root_row, _as_json(relationships) or [],
            fmt or "Child workflow %s not found in database",
        )
        return {
            "o_root_id": root_row["agentic_workflow_id"],
            "o_sub_agent_count": len(children),
            "o_relationship_count": count,
        }

    def _proc_sp_workflow_snapshot_create(
        self, wf_id: Any, comment: Any, *_placeholders: Any
    ) -> dict[str, Any]:
        agent = self._require_agent(str(wf_id))
        snapshot_json = dict(agent["raw_json"])
        snapshot_json.update({"nodes": agent["nodes"], "edges": agent["edges"]})
        snapshot = {
            "id": str(uuid.uuid4()),
            "agent_workflow_id": agent["id"],
            "snapshot_json": snapshot_json,
            "comment": comment or "",
            "created_at": _now(),
        }
        self.workflow_snapshot.append(snapshot)
        return {"o_snapshot_id": snapshot["id"], "o_created_at": snapshot["created_at"]}

    def _proc_sp_agent_embedding_store(
        self, wf_id: Any, vector: Any, text: Any, *_placeholders: Any
    ) -> dict[str, Any]:
        agent = self._require_agent(str(wf_id))
        parsed = _as_json(vector) or []
        agent["embedding_vector"] = parsed
        agent["embedding_text"] = text or ""
        agent["embedding_updated_at"] = _now()
        return {"o_dimensions": len(parsed)}

    def _proc_sp_node_type_upsert(self, defs: Any, *_placeholders: Any) -> dict[str, Any]:
        rows = _as_json(defs) or []
        for row in rows:
            existing = next(
                (n for n in self.node_type_definition if n["type"] == row["type"]), None
            )
            if existing is None:
                self.node_type_definition.append({**row, "is_active": True})
            else:
                existing.update({**row, "is_active": True})
        return {"o_count": len(rows)}

    def _proc_sp_tool_upsert(self, defs: Any, *_placeholders: Any) -> dict[str, Any]:
        rows = _as_json(defs) or []
        for row in rows:
            existing = next((t for t in self.tool_definition if t["name"] == row["name"]), None)
            if existing is None:
                self.tool_definition.append({**row, "is_active": True})
            else:
                existing.update({**row, "is_active": True})
        return {"o_count": len(rows)}

    def _require_agent(self, wf_id: str) -> dict[str, Any]:
        agent = next(
            (a for a in self.agent_workflow if a["agentic_workflow_id"] == wf_id), None
        )
        if agent is None:
            raise NotFoundError(f"agent {wf_id} not found")
        return agent

    # -- remaining port surface -------------------------------------------

    async def function(
        self,
        name: str,
        args: dict[str, Any] | list[Any] | None = None,
        *,
        scalar: bool = False,
        trace_id: str | None = None,
    ) -> QueryOut:
        raise NotFoundError(f"unknown function {name!r}")

    async def batch(
        self, items: list[BatchItem], *, mode: str = "parallel", trace_id: str | None = None
    ) -> BatchResult:
        results = []
        for item in items:
            payload = dict(item.payload)
            out = await self.view(
                payload["name"],
                columns=payload.get("columns"),
                filters=[Filter.model_validate(f) for f in payload.get("filters", [])],
                order_by=[OrderBy.model_validate(o) for o in payload.get("order_by", [])],
                limit=payload.get("limit"),
                offset=payload.get("offset"),
            )
            results.append(
                BatchItemResult(
                    id=item.id, status="ok", rows=out.dict_rows(), row_count=out.row_count
                )
            )
        return BatchResult(
            mode=mode, elapsed_ms=0.0, ok_count=len(results), error_count=0, results=results
        )

    async def ready(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


def _as_json(value: Any) -> Any:
    """Arguments cross the real wire as JSON text; accept either form."""
    if isinstance(value, str):
        import json

        return json.loads(value)
    return value


def _matches(actual: Any, f: Filter) -> bool:
    op, expected = f.op, f.value
    if op is FilterOp.IS_NULL:
        return actual is None
    if op is FilterOp.IS_NOT_NULL:
        return actual is not None
    if op is FilterOp.IN:
        return actual in (expected or [])
    if op is FilterOp.NOT_IN:
        return actual not in (expected or [])
    if op is FilterOp.BETWEEN:
        low, high = expected
        return low <= actual <= high
    if actual is None or expected is None:
        return (actual == expected) if op is FilterOp.EQ else (
            actual != expected if op is FilterOp.NE else False
        )
    if op is FilterOp.EQ:
        return bool(actual == expected)
    if op is FilterOp.NE:
        return bool(actual != expected)
    if op is FilterOp.LT:
        return bool(actual < expected)
    if op is FilterOp.LE:
        return bool(actual <= expected)
    if op is FilterOp.GT:
        return bool(actual > expected)
    if op is FilterOp.GE:
        return bool(actual >= expected)
    if op is FilterOp.LIKE:
        return _like(str(actual), str(expected), case_sensitive=True)
    if op is FilterOp.ILIKE:
        return _like(str(actual), str(expected), case_sensitive=False)
    return False


def _like(value: str, pattern: str, *, case_sensitive: bool) -> bool:
    import re

    regex = "^" + re.escape(pattern).replace("%", ".*").replace("_", ".") + "$"
    return re.match(regex, value, 0 if case_sensitive else re.IGNORECASE) is not None
