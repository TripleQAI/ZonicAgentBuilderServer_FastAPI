-- 999_drop_all.sql — remove the objects THIS project created.
--
-- The base tables are NOT dropped. They belong to the Django app and may hold
-- real data; dropping them here would be a data-loss trap in a teardown script.
-- The table drop is at the bottom, commented out, for test databases only.

DROP VIEW IF EXISTS
    agent_builder.v_schema_migration,
    agent_builder.v_tool_active,
    agent_builder.v_node_type_active,
    agent_builder.v_package_agent,
    agent_builder.v_agent_relationship_detail,
    agent_builder.v_agent_export,
    agent_builder.v_agent_detail,
    agent_builder.v_agent_summary CASCADE;

DROP PROCEDURE IF EXISTS agent_builder.sp_tool_upsert(jsonb, integer);
DROP PROCEDURE IF EXISTS agent_builder.sp_node_type_upsert(jsonb, integer);
DROP PROCEDURE IF EXISTS agent_builder.sp_agent_embedding_store(uuid, jsonb, text, integer);
DROP PROCEDURE IF EXISTS agent_builder.sp_workflow_snapshot_create(uuid, text, uuid, timestamptz);
DROP PROCEDURE IF EXISTS
    agent_builder.sp_agent_package_import(jsonb, jsonb, jsonb, text, uuid, integer, integer);
DROP PROCEDURE IF EXISTS
    agent_builder.sp_agent_workflow_save(jsonb, jsonb, text, integer, integer, integer);

DROP FUNCTION IF EXISTS agent_builder.fn_agent_relationship_replace(uuid, uuid, jsonb, text);
DROP FUNCTION IF EXISTS agent_builder.fn_agent_workflow_upsert(jsonb);
DROP FUNCTION IF EXISTS
    agent_builder.fn_raw_json_overlay(jsonb, jsonb, agent_builder."agentBuilder_agentworkflow");
DROP FUNCTION IF EXISTS agent_builder.fn_agent_workflow_defaults();

DROP TRIGGER IF EXISTS trg_tool_definition_updated_at
    ON agent_builder."agentBuilder_tooldefinition";
DROP TRIGGER IF EXISTS trg_agent_relationship_updated_at
    ON agent_builder."agentBuilder_agentrelationship";
DROP TRIGGER IF EXISTS trg_agent_workflow_updated_at
    ON agent_builder."agentBuilder_agentworkflow";
DROP FUNCTION IF EXISTS agent_builder.set_updated_at();

DROP TABLE IF EXISTS agent_builder.schema_migrations;

-- ==========================================================================
-- TEST DATABASES ONLY. Uncomment to drop the Django-owned tables as well.
-- This destroys every workflow, relationship and snapshot.
-- ==========================================================================
-- DROP TABLE IF EXISTS
--     agent_builder."agentBuilder_workflowsnapshot",
--     agent_builder."agentBuilder_agentrelationship",
--     agent_builder."agentBuilder_agentworkflowchip",
--     agent_builder."agentBuilder_tooldefinition",
--     agent_builder."agentBuilder_nodetypedefinition",
--     agent_builder."agentBuilder_agentworkflow" CASCADE;
