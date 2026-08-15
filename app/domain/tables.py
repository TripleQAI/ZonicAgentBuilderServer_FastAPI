"""RelationSpec / ProcedureSpec — the only place database object names live.

Adding a column touches exactly two files: ``db/002_schema.sql`` and this one.
Nothing else in the backend mentions a column name (MIGRATION_PLAN.md §7.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.gateway.models import OrderBy

# --------------------------------------------------------------------------
# Relation (view) specs
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RelationSpec:
    """One named view, its key, and the columns the application reads."""

    relation: str
    key: str
    columns: tuple[str, ...]
    default_order: tuple[OrderBy, ...] = ()

    def column_list(self) -> list[str]:
        return list(self.columns)

    def order_list(self) -> list[OrderBy]:
        return list(self.default_order)


AGENT_SUMMARY = RelationSpec(
    relation="v_agent_summary",
    key="agentic_workflow_id",
    columns=(
        "agentic_workflow_id", "name", "display_name", "is_root",
        "environment", "updated_at", "node_count", "edge_count",
    ),
    default_order=(OrderBy(column="updated_at", descending=True),),
)

AGENT_DETAIL = RelationSpec(
    relation="v_agent_detail",
    key="agentic_workflow_id",
    columns=(
        "agentic_workflow_id", "name", "display_name", "description", "bpc",
        "is_root", "parent_package_id", "semantic_search_enabled", "updated_at",
        "detail_json",
    ),
)

AGENT_EXPORT = RelationSpec(
    relation="v_agent_export",
    key="agentic_workflow_id",
    columns=("agentic_workflow_id", "parent_package_id", "is_root", "export_json"),
)

RELATIONSHIP_DETAIL = RelationSpec(
    relation="v_agent_relationship_detail",
    key="parent_agentic_workflow_id",
    columns=(
        "id", "parent_agentic_workflow_id", "child_agentic_workflow_id",
        "source_node_id", "source_node_name", "source_node_type",
        "relationship_type", "config_inputs", "is_resolved", "validation_message",
        "child_name", "child_display_name", "child_node_count", "child_edge_count",
    ),
)

PACKAGE_AGENT = RelationSpec(
    relation="v_package_agent",
    key="parent_package_id",
    columns=(
        "parent_package_id", "agentic_workflow_id", "name", "display_name", "is_root",
    ),
)

NODE_TYPE = RelationSpec(
    relation="v_node_type_active",
    key="type",
    columns=(
        "type", "label", "icon", "color", "description", "default_name_prefix",
        "default_config", "handles", "form_schema", "output_schema",
        "validation_schema", "sort_order",
    ),
    default_order=(OrderBy(column="sort_order"),),
)

TOOL = RelationSpec(
    relation="v_tool_active",
    key="name",
    columns=("name", "title", "description", "tool_type", "schema", "default_config"),
)

SCHEMA_MIGRATION = RelationSpec(
    relation="v_schema_migration",
    key="version",
    columns=("version", "applied_at", "checksum"),
)


# --------------------------------------------------------------------------
# Procedure specs
#
# `placeholders` is the number of trailing NULLs the caller must send for the
# procedure's INOUT parameters — the gateway's documented CALL convention. The
# repository appends them, so no call site counts NULLs by hand.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcedureSpec:
    name: str
    arity: int          # positional input arguments
    placeholders: int   # INOUT outputs, sent as NULL
    returns: tuple[str, ...] = field(default_factory=tuple)


SAVE_AGENT = ProcedureSpec(
    name="sp_agent_workflow_save",
    arity=3,
    placeholders=3,
    returns=("o_relationship_count", "o_node_count", "o_edge_count"),
)

IMPORT_PACKAGE = ProcedureSpec(
    name="sp_agent_package_import",
    arity=4,
    placeholders=3,
    returns=("o_root_id", "o_sub_agent_count", "o_relationship_count"),
)

CREATE_SNAPSHOT = ProcedureSpec(
    name="sp_workflow_snapshot_create",
    arity=2,
    placeholders=2,
    returns=("o_snapshot_id", "o_created_at"),
)

STORE_EMBEDDING = ProcedureSpec(
    name="sp_agent_embedding_store",
    arity=3,
    placeholders=1,
    returns=("o_dimensions",),
)

UPSERT_NODE_TYPES = ProcedureSpec(
    name="sp_node_type_upsert", arity=1, placeholders=1, returns=("o_count",)
)

UPSERT_TOOLS = ProcedureSpec(
    name="sp_tool_upsert", arity=1, placeholders=1, returns=("o_count",)
)
