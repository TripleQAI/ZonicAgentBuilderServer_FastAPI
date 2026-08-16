-- 011_grants.sql — least privilege for the role the gateway connects as.
--
-- Defence in depth (MIGRATION_PLAN.md §8.12): raw SQL is disabled at the
-- gateway AND table-level DML is revoked here, so the write surface is exactly
-- the procedures below even if the first control were misconfigured. The
-- procedures are SECURITY DEFINER, so they still write the tables while the
-- caller cannot.
--
-- Name the role first, then run this file. No psql meta-commands are used, so
-- it works in a web SQL editor as well as in psql:
--
--     SET agentbuilder.role = 'agentbuilder_app';
--     \i db/011_grants.sql          -- or paste the rest of this file
--
-- OPTIONAL. Skip it if the gateway connects as the database owner, which is the
-- usual arrangement on a managed service such as Tiger Cloud — an owner cannot
-- be meaningfully restricted this way, and REVOKE on your own tables is a
-- no-op. It earns its place when the gateway has a dedicated, non-owner role.
--
-- WARNING: if Django still writes to these tables it must connect as a
-- different role, or it will lose its own INSERT/UPDATE rights.

DO $$
DECLARE
    v_role text := NULLIF(current_setting('agentbuilder.role', true), '');
BEGIN
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'no role named'
            USING HINT = 'Run:  SET agentbuilder.role = ''your_role'';  first.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_role) THEN
        RAISE EXCEPTION 'role % does not exist', v_role;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_namespace n
        JOIN pg_roles r ON r.oid = n.nspowner
        WHERE n.nspname = 'agent_builder' AND r.rolname = v_role
    ) THEN
        RAISE NOTICE
            'Role % owns the agent_builder schema, so REVOKE cannot restrict it. '
            'Granting reads and executes anyway; skip this file unless you have a '
            'dedicated non-owner role for the gateway.', v_role;
    END IF;

    EXECUTE format('GRANT USAGE ON SCHEMA agent_builder TO %I', v_role);

    -- Reads: views only. No SELECT on the base tables is required by the app.
    EXECUTE format('GRANT SELECT ON
                    agent_builder.v_agent_summary,
                    agent_builder.v_agent_detail,
                    agent_builder.v_agent_export,
                    agent_builder.v_agent_relationship_detail,
                    agent_builder.v_package_agent,
                    agent_builder.v_node_type_active,
                    agent_builder.v_tool_active,
                    agent_builder.v_schema_migration TO %I', v_role);

    -- Writes: procedures only.
    EXECUTE format('GRANT EXECUTE ON PROCEDURE
        agent_builder.sp_agent_workflow_save(jsonb, jsonb, text, integer, integer, integer),
        agent_builder.sp_agent_package_import(jsonb, jsonb, jsonb, text, uuid, integer, integer),
        agent_builder.sp_workflow_snapshot_create(uuid, text, uuid, timestamptz),
        agent_builder.sp_agent_embedding_store(uuid, jsonb, text, integer),
        agent_builder.sp_node_type_upsert(jsonb, integer),
        agent_builder.sp_tool_upsert(jsonb, integer) TO %I', v_role);

    -- Explicitly no direct DML on the base tables.
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON
                    agent_builder."agentBuilder_agentworkflow",
                    agent_builder."agentBuilder_agentrelationship",
                    agent_builder."agentBuilder_agentworkflowchip",
                    agent_builder."agentBuilder_workflowsnapshot",
                    agent_builder."agentBuilder_nodetypedefinition",
                    agent_builder."agentBuilder_tooldefinition"
                    FROM %I', v_role);

    RAISE NOTICE 'Grants applied for %.', v_role;
END;
$$;

INSERT INTO agent_builder.schema_migrations (version) VALUES ('011_grants')
    ON CONFLICT (version) DO UPDATE SET applied_at = now();
