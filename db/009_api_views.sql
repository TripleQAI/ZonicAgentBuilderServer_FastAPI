-- 009_api_views.sql — THE READ SURFACE.
--
-- Every read the application performs names one of these views. The gateway's
-- ViewIn payload cannot join or express OR, so all shaping happens here
-- (MIGRATION_PLAN.md §8.9). Views contain shaping, never policy.
--
-- Idempotent: CREATE OR REPLACE throughout.

-- --------------------------------------------------------------------------
-- v_agent_summary — the agent list and the Agent Explorer.
-- Node/edge counts are computed in SQL instead of len() per row in Python.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_agent_summary AS
SELECT
    a.agentic_workflow_id,
    a.name,
    a.display_name,
    a.is_root,
    a.environment,
    a.updated_at,
    CASE WHEN jsonb_typeof(a.nodes) = 'array' THEN jsonb_array_length(a.nodes) ELSE 0 END
        AS node_count,
    CASE WHEN jsonb_typeof(a.edges) = 'array' THEN jsonb_array_length(a.edges) ELSE 0 END
        AS edge_count
FROM agent_workflow a;

-- --------------------------------------------------------------------------
-- v_agent_detail — GET /agents/{id}.
--
-- detail_json reproduces the Django view exactly: raw_json, with the
-- first-class columns and the four semantic fields overlaid on top.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_agent_detail AS
SELECT
    a.agentic_workflow_id,
    a.name,
    a.display_name,
    a.description,
    a.bpc,
    a.is_root,
    a.parent_package_id,
    a.semantic_search_enabled,
    a.updated_at,
    a.raw_json
        || jsonb_build_object(
               'agenticWorkflowId',     a.agentic_workflow_id,
               'nodes',                 a.nodes,
               'edges',                 a.edges,
               'variables',             a.variables,
               'interface',             a.interface,
               'skills',                a.skills,
               'publishChannels',       a.publish_channels,
               'security',              a.security,
               'semanticSearchEnabled', a.semantic_search_enabled,
               'semanticDomain',        a.semantic_domain,
               'semanticKeywords',      a.semantic_keywords,
               'semanticUseCases',      a.semantic_use_cases
           ) AS detail_json
FROM agent_workflow a;

-- --------------------------------------------------------------------------
-- v_agent_export — THE raw_json overlay contract, expressed once.
--
-- export_single() in the Django app starts from raw_json and overwrites the
-- seven first-class fields. Both /export and /export-package read this view,
-- so the rule cannot drift between them.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_agent_export AS
SELECT
    a.agentic_workflow_id,
    a.parent_package_id,
    a.is_root,
    a.raw_json
        || jsonb_build_object(
               'nodes',           a.nodes,
               'edges',           a.edges,
               'variables',       a.variables,
               'interface',       a.interface,
               'skills',          a.skills,
               'publishChannels', a.publish_channels,
               'security',        a.security
           ) AS export_json
FROM agent_workflow a;

-- --------------------------------------------------------------------------
-- v_agent_relationship_detail — the relationship map in ONE read.
-- The Django implementation issues one extra query per child.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_agent_relationship_detail AS
SELECT
    r.id,
    r.parent_agentic_workflow_id,
    r.child_agentic_workflow_id,
    r.source_node_id,
    r.source_node_name,
    r.source_node_type,
    r.relationship_type,
    r.config_inputs,
    r.is_resolved,
    r.validation_message,
    c.name              AS child_name,
    c.display_name      AS child_display_name,
    CASE WHEN c.id IS NULL THEN 0
         WHEN jsonb_typeof(c.nodes) = 'array' THEN jsonb_array_length(c.nodes)
         ELSE 0 END     AS child_node_count,
    CASE WHEN c.id IS NULL THEN 0
         WHEN jsonb_typeof(c.edges) = 'array' THEN jsonb_array_length(c.edges)
         ELSE 0 END     AS child_edge_count
FROM agent_relationship r
LEFT JOIN agent_workflow c ON c.id = r.child_agent_id;

-- --------------------------------------------------------------------------
-- v_package_agent — package membership, used by export-debug and the
-- "unreferenced sub-agents" warning.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_package_agent AS
SELECT
    a.parent_package_id,
    a.agentic_workflow_id,
    a.name,
    a.display_name,
    a.is_root
FROM agent_workflow a
WHERE a.parent_package_id IS NOT NULL;

-- --------------------------------------------------------------------------
-- Registry reads.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_node_type_active AS
SELECT
    n.type,
    n.label,
    n.icon,
    n.color,
    n.description,
    n.default_name_prefix,
    n.default_config,
    n.handles,
    n.form_schema,
    n.output_schema,
    n.validation_schema,
    n.sort_order
FROM node_type_definition n
WHERE n.is_active;

CREATE OR REPLACE VIEW v_tool_active AS
SELECT
    t.name,
    t.title,
    t.description,
    t.tool_type,
    t.schema,
    t.default_config
FROM tool_definition t
WHERE t.is_active;

-- --------------------------------------------------------------------------
-- v_schema_migration — lets the app report what is deployed. It warns; it
-- never migrates.
-- --------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_schema_migration AS
SELECT version, applied_at, checksum FROM schema_migrations;

INSERT INTO schema_migrations (version) VALUES ('009_api_views')
    ON CONFLICT (version) DO UPDATE SET applied_at = now();
