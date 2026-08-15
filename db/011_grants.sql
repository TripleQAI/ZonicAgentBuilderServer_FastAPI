-- 011_grants.sql — least privilege for the role the gateway connects as.
--
-- Defence in depth (MIGRATION_PLAN.md §8.11): raw SQL is disabled at the
-- gateway AND table-level DML is revoked here, so the write surface is exactly
-- the procedures below even if the first control were misconfigured.
--
-- Set the role name before running, or export PGF_ROLE and use psql -v:
--     psql -v pgf_role=agentbuilder_app -f db/011_grants.sql
-- The default below matches the example DSN in the plan.

\if :{?pgf_role}
\else
\set pgf_role 'fshadmin'
\endif

DO $$
DECLARE
    v_role text := :'pgf_role';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_role) THEN
        RAISE NOTICE 'role % does not exist — skipping grants', v_role;
        RETURN;
    END IF;

    EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', v_role);

    -- Reads: views only. No SELECT on base tables is required by the app.
    EXECUTE format('GRANT SELECT ON v_agent_summary, v_agent_detail, v_agent_export,
                    v_agent_relationship_detail, v_package_agent, v_node_type_active,
                    v_tool_active, v_schema_migration TO %I', v_role);

    -- Writes: procedures only.
    EXECUTE format('GRANT EXECUTE ON PROCEDURE
                    sp_agent_workflow_save(jsonb, jsonb, text, integer, integer, integer),
                    sp_agent_package_import(jsonb, jsonb, jsonb, text, uuid, integer, integer),
                    sp_workflow_snapshot_create(uuid, text, uuid, timestamptz),
                    sp_agent_embedding_store(uuid, jsonb, text, integer),
                    sp_node_type_upsert(jsonb, integer),
                    sp_tool_upsert(jsonb, integer) TO %I', v_role);

    -- Explicitly no INSERT/UPDATE/DELETE on the base tables.
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON
                    agent_workflow, agent_relationship, agent_workflow_chip,
                    workflow_snapshot, node_type_definition, tool_definition
                    FROM %I', v_role);
END;
$$;

INSERT INTO schema_migrations (version) VALUES ('011_grants')
    ON CONFLICT (version) DO UPDATE SET applied_at = now();
