-- 003_functions_triggers.sql — updated_at maintenance.
--
-- Replaces Django's auto_now. Doing it in the database means the timestamp is
-- right whatever wrote the row, including a procedure call (plan §L9).

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_agent_workflow_updated_at ON agent_workflow;
CREATE TRIGGER trg_agent_workflow_updated_at
    BEFORE UPDATE ON agent_workflow
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_agent_relationship_updated_at ON agent_relationship;
CREATE TRIGGER trg_agent_relationship_updated_at
    BEFORE UPDATE ON agent_relationship
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_tool_definition_updated_at ON tool_definition;
CREATE TRIGGER trg_tool_definition_updated_at
    BEFORE UPDATE ON tool_definition
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

INSERT INTO schema_migrations (version) VALUES ('003_functions_triggers')
    ON CONFLICT (version) DO NOTHING;
