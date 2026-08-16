-- 000_preflight.sql — READ ONLY. Changes nothing.
--
-- Run this first, against the real database, and read the output before
-- applying anything else. It answers the questions the installer cannot ask
-- for you: are the tables the ones this service expects, do they already hold
-- data, is anything in the way, and what has already been applied.
--
-- Safe to run in the Tiger Cloud SQL editor: no psql meta-commands. Two
-- statements, and the console shows the last result set — which is the main
-- report. Every row is one check.
--
--   status = OK      nothing to do
--            INFO    context, not a problem
--            ACTION  something will be created or changed
--            BLOCK   fix this before running the installer

-- ---------------------------------------------------------------------------
-- Runs FIRST, and is a separate statement, for two reasons.
--
-- It reads a base table rather than the catalog, so unlike everything below it
-- cannot run at all until that table exists — and a "relation does not exist"
-- error here is itself the diagnosis.
--
-- It is first because a SQL console typically displays only the LAST result
-- set. Putting the small check ahead of the main report means running the whole
-- file shows you the report.
--
-- Duplicate tool names block the unique index 005 creates.
-- ---------------------------------------------------------------------------
SELECT
    '6. tool names' AS check,
    CASE WHEN count(*) = 0 THEN 'OK' ELSE 'BLOCK' END AS status,
    CASE WHEN count(*) = 0
         THEN 'no duplicates — the unique index will apply cleanly'
         ELSE count(*)::text || ' duplicated name(s): ' || string_agg(name, ', ')
              || ' — 005 will refuse until they are resolved' END AS detail
FROM (
    SELECT d.name
    FROM agent_builder."agentBuilder_tooldefinition" d
    GROUP BY d.name HAVING count(*) > 1
) dupes;

WITH
-- Every column this service reads or writes. A missing one means the Django
-- migrations were not all applied, and the installer will refuse to continue.
expected(rel, col) AS (
    VALUES
        ('agentBuilder_agentworkflow', 'id'),
        ('agentBuilder_agentworkflow', 'agentic_workflow_id'),
        ('agentBuilder_agentworkflow', 'name'),
        ('agentBuilder_agentworkflow', 'display_name'),
        ('agentBuilder_agentworkflow', 'is_root'),
        ('agentBuilder_agentworkflow', 'parent_package_id'),
        ('agentBuilder_agentworkflow', 'nodes'),
        ('agentBuilder_agentworkflow', 'edges'),
        ('agentBuilder_agentworkflow', 'variables'),
        ('agentBuilder_agentworkflow', 'interface'),
        ('agentBuilder_agentworkflow', 'skills'),
        ('agentBuilder_agentworkflow', 'publish_channels'),
        ('agentBuilder_agentworkflow', 'security'),
        ('agentBuilder_agentworkflow', 'raw_json'),
        ('agentBuilder_agentworkflow', 'created_at'),
        ('agentBuilder_agentworkflow', 'updated_at'),
        -- migration 0002
        ('agentBuilder_agentworkflow', 'semantic_search_enabled'),
        ('agentBuilder_agentworkflow', 'semantic_domain'),
        ('agentBuilder_agentworkflow', 'semantic_keywords'),
        ('agentBuilder_agentworkflow', 'semantic_use_cases'),
        -- migration 0003
        ('agentBuilder_agentworkflow', 'embedding_vector'),
        ('agentBuilder_agentworkflow', 'embedding_text'),
        ('agentBuilder_agentworkflow', 'embedding_updated_at'),
        ('agentBuilder_agentrelationship', 'id'),
        ('agentBuilder_agentrelationship', 'parent_agent_id'),
        ('agentBuilder_agentrelationship', 'child_agent_id'),
        ('agentBuilder_agentrelationship', 'parent_agentic_workflow_id'),
        ('agentBuilder_agentrelationship', 'child_agentic_workflow_id'),
        ('agentBuilder_agentrelationship', 'source_node_id'),
        ('agentBuilder_agentrelationship', 'source_node_name'),
        ('agentBuilder_agentrelationship', 'source_node_type'),
        ('agentBuilder_agentrelationship', 'relationship_type'),
        ('agentBuilder_agentrelationship', 'config_inputs'),
        ('agentBuilder_agentrelationship', 'agent_info'),
        ('agentBuilder_agentrelationship', 'app_info'),
        ('agentBuilder_agentrelationship', 'module_info'),
        ('agentBuilder_agentrelationship', 'is_resolved'),
        ('agentBuilder_agentrelationship', 'validation_message'),
        -- migration 0004 / 0005
        ('agentBuilder_agentworkflowchip', 'id'),
        ('agentBuilder_agentworkflowchip', 'agentic_workflow_id'),
        ('agentBuilder_agentworkflowchip', 'bpc'),
        ('agentBuilder_agentworkflowchip', 'name'),
        ('agentBuilder_agentworkflowchip', 'display_name'),
        ('agentBuilder_agentworkflowchip', 'description'),
        ('agentBuilder_agentworkflowchip', 'is_disabled'),
        ('agentBuilder_workflowsnapshot', 'id'),
        ('agentBuilder_workflowsnapshot', 'agent_workflow_id'),
        ('agentBuilder_workflowsnapshot', 'snapshot_json'),
        ('agentBuilder_workflowsnapshot', 'comment'),
        ('agentBuilder_workflowsnapshot', 'created_at'),
        ('agentBuilder_nodetypedefinition', 'id'),
        ('agentBuilder_nodetypedefinition', 'type'),
        ('agentBuilder_nodetypedefinition', 'label'),
        ('agentBuilder_nodetypedefinition', 'default_config'),
        ('agentBuilder_nodetypedefinition', 'handles'),
        ('agentBuilder_nodetypedefinition', 'form_schema'),
        ('agentBuilder_nodetypedefinition', 'output_schema'),
        ('agentBuilder_nodetypedefinition', 'validation_schema'),
        ('agentBuilder_nodetypedefinition', 'sort_order'),
        ('agentBuilder_nodetypedefinition', 'is_active'),
        ('agentBuilder_tooldefinition', 'id'),
        ('agentBuilder_tooldefinition', 'name'),
        ('agentBuilder_tooldefinition', 'tool_type'),
        ('agentBuilder_tooldefinition', 'schema'),
        ('agentBuilder_tooldefinition', 'default_config'),
        ('agentBuilder_tooldefinition', 'is_active')
),

-- Objects the installer creates. Listing them says what a re-run will replace.
ours(kind, name) AS (
    VALUES
        ('view', 'v_agent_summary'),
        ('view', 'v_agent_detail'),
        ('view', 'v_agent_export'),
        ('view', 'v_agent_relationship_detail'),
        ('view', 'v_package_agent'),
        ('view', 'v_node_type_active'),
        ('view', 'v_tool_active'),
        ('view', 'v_schema_migration'),
        ('routine', 'fn_agent_workflow_defaults'),
        ('routine', 'fn_raw_json_overlay'),
        ('routine', 'fn_agent_workflow_upsert'),
        ('routine', 'fn_agent_relationship_replace'),
        ('routine', 'sp_agent_workflow_save'),
        ('routine', 'sp_agent_package_import'),
        ('routine', 'sp_workflow_snapshot_create'),
        ('routine', 'sp_agent_embedding_store'),
        ('routine', 'sp_node_type_upsert'),
        ('routine', 'sp_tool_upsert')
)

-- 1. Environment ------------------------------------------------------------
SELECT
    '1. environment'                       AS check,
    'INFO'                                 AS status,
    'PostgreSQL ' || current_setting('server_version') AS detail

UNION ALL
SELECT
    '1. environment',
    CASE WHEN to_regprocedure('gen_random_uuid()') IS NOT NULL THEN 'OK' ELSE 'BLOCK' END,
    CASE WHEN to_regprocedure('gen_random_uuid()') IS NOT NULL
         THEN 'gen_random_uuid() available'
         ELSE 'gen_random_uuid() missing — needs PostgreSQL 13+ or the pgcrypto extension' END

UNION ALL
SELECT
    '2. schema',
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.schemata
                      WHERE schema_name = 'agent_builder') THEN 'OK' ELSE 'ACTION' END,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.schemata
                      WHERE schema_name = 'agent_builder')
         THEN 'agent_builder exists'
         ELSE 'agent_builder will be created' END

-- 2. Tables, and whether they already hold data -----------------------------
UNION ALL
SELECT
    '3. table ' || t.rel,
    CASE WHEN c.oid IS NULL THEN 'ACTION' ELSE 'OK' END,
    CASE WHEN c.oid IS NULL
         THEN 'missing — will be created empty'
         ELSE 'present, ~' || GREATEST(COALESCE(s.n_live_tup, 0),
                                       COALESCE(c.reltuples, 0)::bigint)::text
              || ' row(s) (estimate; ANALYZE for exact)' END
FROM (SELECT DISTINCT rel FROM expected) t
LEFT JOIN pg_class c
       ON c.relname = t.rel
      AND c.relnamespace = to_regnamespace('agent_builder')
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid

-- 3. Columns this service needs ---------------------------------------------
UNION ALL
SELECT
    '4. columns',
    CASE WHEN count(*) = 0 THEN 'OK' ELSE 'BLOCK' END,
    CASE WHEN count(*) = 0
         THEN 'all ' || (SELECT count(*)::text FROM expected) || ' expected columns present'
         ELSE count(*)::text || ' missing: ' || string_agg(rel || '.' || col, ', ') END
FROM (
    SELECT e.rel, e.col
    FROM expected e
    WHERE EXISTS (SELECT 1 FROM pg_class c
                  WHERE c.relname = e.rel
                    AND c.relnamespace = to_regnamespace('agent_builder'))
      AND NOT EXISTS (
          SELECT 1 FROM information_schema.columns ic
          WHERE ic.table_schema = 'agent_builder'
            AND ic.table_name = e.rel
            AND ic.column_name = e.col)
) missing

-- 4. What the installer will create or replace ------------------------------
UNION ALL
SELECT
    '5. ' || o.kind || 's',
    'INFO',
    count(*) FILTER (WHERE present) || ' of ' || count(*)
        || ' already exist and will be replaced'
FROM (
    SELECT
        ours.kind,
        ours.name,
        CASE ours.kind
            WHEN 'view' THEN to_regclass('agent_builder.' || ours.name) IS NOT NULL
            ELSE EXISTS (SELECT 1 FROM pg_proc p
                         WHERE p.proname = ours.name
                           AND p.pronamespace = to_regnamespace('agent_builder'))
        END AS present
    FROM ours
) o
GROUP BY o.kind

ORDER BY 1, 2;
