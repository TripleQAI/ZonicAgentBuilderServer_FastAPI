-- 999_drop_all.sql — tear down everything this project created.
-- Destructive. Intended for test databases and clean re-installs.

DROP VIEW IF EXISTS v_schema_migration, v_tool_active, v_node_type_active,
                    v_package_agent, v_agent_relationship_detail,
                    v_agent_export, v_agent_detail, v_agent_summary CASCADE;

DROP PROCEDURE IF EXISTS sp_tool_upsert(jsonb, integer);
DROP PROCEDURE IF EXISTS sp_node_type_upsert(jsonb, integer);
DROP PROCEDURE IF EXISTS sp_agent_embedding_store(uuid, jsonb, text, integer);
DROP PROCEDURE IF EXISTS sp_workflow_snapshot_create(uuid, text, uuid, timestamptz);
DROP PROCEDURE IF EXISTS sp_agent_package_import(jsonb, jsonb, jsonb, text, uuid, integer, integer);
DROP PROCEDURE IF EXISTS sp_agent_workflow_save(jsonb, jsonb, text, integer, integer, integer);

DROP FUNCTION IF EXISTS fn_agent_relationship_replace(uuid, uuid, jsonb, text);
DROP FUNCTION IF EXISTS fn_agent_workflow_upsert(jsonb);
DROP FUNCTION IF EXISTS set_updated_at();

DROP TABLE IF EXISTS workflow_snapshot, agent_relationship, agent_workflow_chip,
                     tool_definition, node_type_definition, agent_workflow,
                     schema_migrations CASCADE;
