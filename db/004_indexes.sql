-- 004_indexes.sql — indexes the application's access paths actually need.
-- Django created none of these beyond the FK/unique defaults.

CREATE INDEX IF NOT EXISTS idx_agent_workflow_updated_at
    ON agent_workflow (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_workflow_parent_package
    ON agent_workflow (parent_package_id);

CREATE INDEX IF NOT EXISTS idx_agent_workflow_is_root
    ON agent_workflow (is_root) WHERE is_root;

CREATE INDEX IF NOT EXISTS idx_agent_workflow_semantic
    ON agent_workflow (agentic_workflow_id) WHERE semantic_search_enabled;

CREATE INDEX IF NOT EXISTS idx_agent_relationship_parent
    ON agent_relationship (parent_agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_relationship_child
    ON agent_relationship (child_agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_relationship_parent_wf
    ON agent_relationship (parent_agentic_workflow_id);

CREATE INDEX IF NOT EXISTS idx_agent_relationship_parent_resolved
    ON agent_relationship (parent_agent_id, is_resolved);

CREATE INDEX IF NOT EXISTS idx_workflow_snapshot_agent
    ON workflow_snapshot (agent_workflow_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_node_type_definition_active
    ON node_type_definition (sort_order) WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_tool_definition_active
    ON tool_definition (tool_type) WHERE is_active;

INSERT INTO schema_migrations (version) VALUES ('004_indexes')
    ON CONFLICT (version) DO NOTHING;
