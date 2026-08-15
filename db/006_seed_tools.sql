-- 006_seed_tools.sql
--
-- GENERATED FILE — do not edit.
-- Regenerate with:  python scripts/gen_seed_sql.py
-- Source of truth:  app/resources/tools/seed_tools.json
--
-- Idempotent: re-running updates existing rows in place.


INSERT INTO tool_definition (name, title, description, tool_type, schema, default_config, is_active)
VALUES ('http_get', 'HTTP GET', 'Fetch a URL and return the response body.', 'function', '{"type": "object", "properties": {"url": {"type": "string"}, "headers": {"type": "object"}}, "required": ["url"]}'::jsonb, '{}'::jsonb, true)
ON CONFLICT (name) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tool_type = EXCLUDED.tool_type,
    schema = EXCLUDED.schema,
    default_config = EXCLUDED.default_config,
    is_active = true;

INSERT INTO tool_definition (name, title, description, tool_type, schema, default_config, is_active)
VALUES ('db_lookup', 'Database Lookup', 'Read rows from a governed view by name.', 'function', '{"type": "object", "properties": {"view": {"type": "string"}, "filters": {"type": "array"}}, "required": ["view"]}'::jsonb, '{}'::jsonb, true)
ON CONFLICT (name) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tool_type = EXCLUDED.tool_type,
    schema = EXCLUDED.schema,
    default_config = EXCLUDED.default_config,
    is_active = true;

INSERT INTO tool_definition (name, title, description, tool_type, schema, default_config, is_active)
VALUES ('handoff_to_agent', 'Hand Off To Agent', 'Transfer the conversation to another agent node.', 'handoff', '{"type": "object", "properties": {"targetNodeId": {"type": "string"}}, "required": ["targetNodeId"]}'::jsonb, '{}'::jsonb, true)
ON CONFLICT (name) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tool_type = EXCLUDED.tool_type,
    schema = EXCLUDED.schema,
    default_config = EXCLUDED.default_config,
    is_active = true;

INSERT INTO tool_definition (name, title, description, tool_type, schema, default_config, is_active)
VALUES ('show_view', 'Show UI View', 'Render a registered UI view to the user.', 'ui_view', '{"type": "object", "properties": {"viewId": {"type": "string"}, "params": {"type": "object"}}, "required": ["viewId"]}'::jsonb, '{}'::jsonb, true)
ON CONFLICT (name) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tool_type = EXCLUDED.tool_type,
    schema = EXCLUDED.schema,
    default_config = EXCLUDED.default_config,
    is_active = true;

INSERT INTO tool_definition (name, title, description, tool_type, schema, default_config, is_active)
VALUES ('mcp_server', 'MCP Server', 'Tools exposed by a configured MCP server.', 'mcp', '{"type": "object", "properties": {"serverUrl": {"type": "string"}, "transport": {"type": "string", "enum": ["stdio", "sse", "http"]}, "tools": {"type": "array"}}, "required": ["serverUrl"]}'::jsonb, '{"transport": "http", "tools": []}'::jsonb, true)
ON CONFLICT (name) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    tool_type = EXCLUDED.tool_type,
    schema = EXCLUDED.schema,
    default_config = EXCLUDED.default_config,
    is_active = true;

INSERT INTO schema_migrations (version) VALUES ('006_seed_tools')
    ON CONFLICT (version) DO UPDATE SET applied_at = now();
