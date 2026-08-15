-- 005_seed_node_types.sql
--
-- GENERATED FILE — do not edit.
-- Regenerate with:  python scripts/gen_seed_sql.py
-- Source of truth:  app/resources/node_types/*.json
--
-- Idempotent: re-running updates existing rows in place.


INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('start', 'Start', 'bi-play-circle-fill', '#22c55e', 'Entry point of the workflow.', 'Start', '{"interfaceInputs": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": []}'::jsonb, '{"sections": [{"title": "Interface Inputs", "fields": [{"key": "config.interfaceInputs", "label": "Interface Inputs", "type": "schema_builder", "description": "Variables passed in when this workflow is invoked."}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}]}'::jsonb, '{}'::jsonb, '{"rules": []}'::jsonb, 1, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('llm', 'LLM', 'bi-cpu-fill', '#3b82f6', 'Calls a large language model with a prompt.', 'LLM', '{"model": "claude-sonnet-4-6", "messages": [], "tools": [], "responseFormat": "text", "temperature": 0.7, "maxTokens": 1024, "errorHandling": false, "stateUpdates": [], "outputSchema": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Definition", "fields": [{"key": "config.model", "label": "Model", "type": "select", "required": true, "options": [{"value": "claude-opus-4-8", "label": "claude-opus-4-8"}, {"value": "claude-sonnet-4-6", "label": "claude-sonnet-4-6"}, {"value": "claude-haiku-4-5", "label": "claude-haiku-4-5"}], "defaultValue": "claude-sonnet-4-6"}]}, {"title": "Instructions", "fields": [{"key": "config.messages", "label": "Messages", "type": "message_list"}]}, {"title": "Tools", "fields": [{"key": "config.tools", "label": "Tools", "type": "tool_list"}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.responseFormat", "label": "Response Format", "type": "select", "options": [{"value": "text", "label": "Plain Text"}, {"value": "json", "label": "JSON Object"}], "defaultValue": "text"}, {"key": "config.temperature", "label": "Temperature", "type": "number", "min": 0, "max": 2, "step": 0.1, "defaultValue": 0.7}, {"key": "config.maxTokens", "label": "Max Tokens", "type": "number", "defaultValue": 1024}, {"key": "config.errorHandling", "label": "Enable Error Handling", "type": "switch", "defaultValue": false}]}]}'::jsonb, '{"type": "object", "properties": {"text": {"type": "string"}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 2, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('agent', 'Agent', 'bi-robot', '#6366f1', 'Invokes an agentic loop with tools and a model.', 'Agent', '{"model": "claude-sonnet-4-6", "strategy": "react", "systemPrompt": "", "tools": [], "maxIterations": 10, "includeThoughts": false, "stateUpdates": [], "outputSchema": [], "handoffTarget": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Definition", "fields": [{"key": "config.model", "label": "Model", "type": "select", "required": true, "options": [{"value": "claude-opus-4-8", "label": "claude-opus-4-8"}, {"value": "claude-sonnet-4-6", "label": "claude-sonnet-4-6"}, {"value": "claude-haiku-4-5", "label": "claude-haiku-4-5"}], "defaultValue": "claude-sonnet-4-6"}, {"key": "config.strategy", "label": "Agent Strategy", "type": "select", "options": [{"value": "react", "label": "ReAct"}, {"value": "plan_exec", "label": "Plan + Execute"}, {"value": "custom", "label": "Custom"}], "defaultValue": "react"}]}, {"title": "Instructions", "fields": [{"key": "config.systemPrompt", "label": "System Prompt", "type": "markdown"}]}, {"title": "Tools", "fields": [{"key": "config.tools", "label": "Tools", "type": "tool_list"}]}, {"title": "Handoff", "fields": [{"key": "config.handoffTarget", "label": "Handoff Targets", "type": "node_multiselect", "description": "When this agent completes, hand off execution to each selected node."}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.maxIterations", "label": "Max Iterations", "type": "number", "defaultValue": 10}, {"key": "config.includeThoughts", "label": "Include Thoughts", "type": "switch", "defaultValue": false}]}]}'::jsonb, '{"type": "object"}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 3, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('external_agent', 'External Agent', 'bi-box-arrow-up-right', '#a855f7', 'Calls an agent hosted externally via HTTP.', 'ExtAgent', '{"endpoint": "", "authType": "none", "apiKey": "", "inputMapping": [], "outputSchema": [], "timeoutSeconds": 30, "retries": 0, "stateUpdates": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Connection", "fields": [{"key": "config.endpoint", "label": "Endpoint URL", "type": "expression", "required": true, "description": "Full URL of the external agent endpoint."}, {"key": "config.authType", "label": "Auth Type", "type": "select", "options": [{"value": "none", "label": "None"}, {"value": "bearer", "label": "Bearer Token"}, {"value": "apikey", "label": "API Key Header"}, {"value": "basic", "label": "Basic Auth"}], "defaultValue": "none"}, {"key": "config.apiKey", "label": "API Key / Token", "type": "expression", "description": "Supports variable references, e.g. {{secrets.myKey}}"}]}, {"title": "Input Mapping", "fields": [{"key": "config.inputMapping", "label": "Input Fields", "type": "mapping_list"}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.timeoutSeconds", "label": "Timeout (seconds)", "type": "number", "defaultValue": 30}, {"key": "config.retries", "label": "Retries", "type": "number", "defaultValue": 0}]}]}'::jsonb, '{"type": "object"}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 4, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('script', 'Script', 'bi-file-code-fill', '#eab308', 'Runs a custom JavaScript or Python snippet.', 'Script', '{"language": "javascript", "code": "/**\n * Example Script\n *\n * Inputs are available on the `input` object.\n * Example: `input.score` (from Input Variables section).\n *\n * Return an object that matches the Output schema.\n * - In this node, you can read it as `nodeOutput.result`.\n * - In other nodes, use: `nodes.<nodeName>.result.<field>`\n */\n\nreturn {};\n", "inputs": [], "outputSchema": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Input Variables", "fields": [{"key": "config.inputs", "label": "Input Mapping", "type": "mapping_list", "description": "Mapped variables are accessible in the code as input.key — e.g. input.queryResponse."}]}, {"title": "Script", "fields": [{"key": "config.language", "label": "Language", "type": "select", "required": true, "options": [{"value": "javascript", "label": "JavaScript"}, {"value": "python", "label": "Python"}, {"value": "typescript", "label": "TypeScript"}], "defaultValue": "javascript"}, {"key": "config.code", "label": "Code", "type": "code", "required": true, "rows": 10}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}]}'::jsonb, '{"type": "object"}'::jsonb, '{"rules": ["required_name", "required_code"]}'::jsonb, 5, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('http_request', 'HTTP Request', 'bi-cloud-arrow-up-fill', '#06b6d4', 'Makes an outbound HTTP request.', 'HTTP', '{"method": "GET", "url": "", "headers": [], "body": "", "outputSchema": [], "timeoutSeconds": 30, "stateUpdates": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Request", "fields": [{"key": "config.method", "label": "Method", "type": "select", "required": true, "options": [{"value": "GET", "label": "GET"}, {"value": "POST", "label": "POST"}, {"value": "PUT", "label": "PUT"}, {"value": "PATCH", "label": "PATCH"}, {"value": "DELETE", "label": "DELETE"}], "defaultValue": "GET"}, {"key": "config.url", "label": "URL", "type": "expression", "required": true, "description": "Supports variable references in the URL."}]}, {"title": "Headers", "fields": [{"key": "config.headers", "label": "Request Headers", "type": "key_value_list"}]}, {"title": "Body", "fields": [{"key": "config.body", "label": "Request Body", "type": "expression", "rows": 4, "description": "Supports variable references."}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.timeoutSeconds", "label": "Timeout (seconds)", "type": "number", "defaultValue": 30}]}]}'::jsonb, '{"type": "object", "properties": {"status": {"type": "integer"}, "body": {"type": "string"}}}'::jsonb, '{"rules": ["required_name", "required_url"]}'::jsonb, 6, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('guardrail', 'Guardrail', 'bi-shield-fill-check', '#ef4444', 'Enforces safety or policy constraints on the flow.', 'Guardrail', '{"inputMapping": [], "policy": "", "action": "block", "outputSchema": [], "stateUpdates": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "pass", "position": "bottom", "label": "Pass"}, {"id": "fail", "position": "right", "label": "Fail"}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Input Mapping", "fields": [{"key": "config.inputMapping", "label": "Input Mapping", "type": "mapping_list"}]}, {"title": "Policy", "fields": [{"key": "config.policy", "label": "Policy / Rules", "type": "textarea", "required": true, "rows": 4}, {"key": "config.action", "label": "On Fail", "type": "select", "required": true, "options": [{"value": "block", "label": "Block"}, {"value": "warn", "label": "Warn"}, {"value": "redirect", "label": "Redirect"}], "defaultValue": "block"}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}]}'::jsonb, '{"type": "object", "properties": {"passed": {"type": "boolean"}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 7, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('rule', 'Rule', 'bi-funnel-fill', '#f97316', 'Evaluates conditional branches; each rule generates a canvas handle.', 'Rule', '{"rules": [{"ruleId": "r_default", "label": "True", "conditions": [], "conditionLogic": "AND"}, {"ruleId": "r_else", "label": "Else", "isDefault": true, "conditions": [], "conditionLogic": "AND"}], "outputSchema": []}'::jsonb, '{"sources": [{"id": "r_default", "position": "bottom", "label": "True"}, {"id": "r_else", "position": "bottom", "label": "Else"}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Rule Branches", "fields": [{"key": "config.rules", "label": "Rules", "type": "condition_builder", "description": "Each rule creates a named output handle on the canvas node."}]}]}'::jsonb, '{"type": "object", "properties": {"matchedRule": {"type": "string"}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 8, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('workflow', 'Sub Flow', 'bi-diagram-3-fill', '#14b8a6', 'Executes a child agent workflow as a sub-flow.', 'SubFlow', '{"agenticWorkflowId": "", "inputs": [], "outputSchema": [], "stateUpdates": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Sub Flow Reference", "fields": [{"key": "config.agenticWorkflowId", "label": "Child Workflow", "type": "agentic_workflow_selector", "required": true, "description": "Select a loaded agent to reference as a sub-flow."}, {"key": "config.agenticWorkflowId", "label": "Relationship Status", "type": "relationship_status"}]}, {"title": "Input Mapping", "fields": [{"key": "config.inputs", "label": "Inputs", "type": "mapping_list"}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}]}'::jsonb, '{"type": "object"}'::jsonb, '{"rules": ["required_name", "required_agentic_workflow_id"]}'::jsonb, 9, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('variable', 'Variable Update', 'bi-sliders', '#84cc16', 'Reads or writes workflow variables.', 'VarUpdate', '{"updates": [], "outputSchema": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Variable Updates", "fields": [{"key": "config.updates", "label": "Updates", "type": "state_update_list"}]}]}'::jsonb, '{}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 10, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('output', 'Output', 'bi-box-arrow-right', '#10b981', 'Terminal output node — ends the workflow and returns a result.', 'Output', '{"variableUpdates": []}'::jsonb, '{"sources": [], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}]}'::jsonb, '{}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 11, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('approval', 'Approval', 'bi-hand-thumbs-up-fill', '#f59e0b', 'Pauses the workflow for a human approval gate.', 'Approval', '{"message": "", "approvers": [], "timeoutHours": 24, "responseVariable": "approval.response", "outputSchema": [], "stateUpdates": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "approved", "position": "bottom", "label": "Approved"}, {"id": "rejected", "position": "right", "label": "Rejected"}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Approval Request", "fields": [{"key": "config.message", "label": "Approval Message", "type": "textarea", "rows": 3}, {"key": "config.approvers", "label": "Approvers", "type": "key_value_list", "description": "List approver identifiers (email, userId, role)."}, {"key": "config.timeoutHours", "label": "Timeout (hours)", "type": "number", "defaultValue": 24}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.responseVariable", "label": "Response Variable Path", "type": "text", "defaultValue": "approval.response", "description": "Variable path to store the approval response."}]}]}'::jsonb, '{"type": "object", "properties": {"approved": {"type": "boolean"}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 12, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('human_input', 'Human Input', 'bi-person-fill', '#0ea5e9', 'Pauses the workflow to collect input from a human user.', 'HumanInput', '{"prompt": "", "inputType": "text", "required": true, "responseVariable": "human.response", "outputSchema": [], "stateUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Input Configuration", "fields": [{"key": "config.prompt", "label": "Prompt", "type": "textarea", "required": true, "rows": 3}, {"key": "config.inputType", "label": "Input Type", "type": "select", "required": true, "options": [{"value": "text", "label": "Text"}, {"value": "number", "label": "Number"}, {"value": "file", "label": "File"}, {"value": "choice", "label": "Multiple Choice"}], "defaultValue": "text"}, {"key": "config.required", "label": "Required", "type": "switch", "defaultValue": true}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.responseVariable", "label": "Response Variable Path", "type": "text", "defaultValue": "human.response", "description": "Variable path to store the collected input."}, {"key": "config.stateUpdates", "label": "State Updates", "type": "state_update_list"}]}]}'::jsonb, '{"type": "object", "properties": {"value": {"type": "string"}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 13, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('tool', 'Tool', 'bi-tools', '#7c3aed', 'Invokes a registered tool (function, MCP, handoff, or UI view).', 'Tool', '{"toolName": "", "toolType": "function", "inputs": [], "outputSchema": [], "handoffTarget": "", "schema": {}, "stateUpdates": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Tool Configuration", "fields": [{"key": "config.toolName", "label": "Tool Name", "type": "text", "required": true}, {"key": "config.toolType", "label": "Tool Type", "type": "select", "options": [{"value": "function", "label": "Function"}, {"value": "handoff", "label": "Handoff"}, {"value": "ui_view", "label": "UI View"}, {"value": "mcp", "label": "MCP"}], "defaultValue": "function"}]}, {"title": "Input Mapping", "fields": [{"key": "config.inputs", "label": "Inputs", "type": "mapping_list"}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.handoffTarget", "label": "Handoff Target Node ID", "type": "text", "description": "Required when toolType is ''handoff''."}, {"key": "config.schema", "label": "Tool Schema", "type": "json"}]}]}'::jsonb, '{"type": "object"}'::jsonb, '{"rules": ["required_name", "required_tool_name"]}'::jsonb, 14, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('note', 'Note', 'bi-sticky-fill', '#6b7280', 'A non-executing annotation placed on the canvas.', 'Note', '{"text": "", "color": "#6b7280"}'::jsonb, '{"sources": [], "targets": []}'::jsonb, '{"sections": [{"title": "Note Content", "fields": [{"key": "config.text", "label": "Note Text", "type": "textarea", "rows": 5}, {"key": "config.color", "label": "Color", "type": "select", "options": [{"value": "#6b7280", "label": "Gray"}, {"value": "#f9e2af", "label": "Yellow"}, {"value": "#89dceb", "label": "Sky Blue"}, {"value": "#a6e3a1", "label": "Green"}, {"value": "#f38ba8", "label": "Red"}], "defaultValue": "#6b7280"}]}]}'::jsonb, '{}'::jsonb, '{"rules": []}'::jsonb, 15, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('view', 'View', 'bi-filetype-html', '#ec4899', 'Prepares an HTML fragment that can embed node results and flow variable data.', 'View', '{"viewMode": "html_template", "htmlTemplate": "<div>\n  <!-- Reference variables with {{variable.path}} -->\n</div>", "templateConfig": "{\n  \"data\": {},\n  \"html_template\": \"\",\n  \"attached_config\": {}\n}", "outputSchema": [], "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "HTML Template", "fields": [{"key": "config.viewMode", "label": "HTML Template", "type": "view_template", "required": true}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}]}'::jsonb, '{"type": "object", "properties": {"html": {"type": "string"}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 16, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO node_type_definition (type, label, icon, color, description, default_name_prefix, default_config, handles, form_schema, output_schema, validation_schema, sort_order, is_active)
VALUES ('db_query', 'DB Query', 'bi-database-fill', '#0284c7', 'Executes a SQL query against a configured database connection.', 'DBQuery', '{"connectionId": "", "databaseType": "postgresql", "query": "", "parameters": [], "maxRows": 1000, "timeoutSeconds": 30, "outputSchema": [], "rowSchema": {}, "variableUpdates": []}'::jsonb, '{"sources": [{"id": "default", "position": "bottom", "label": ""}], "targets": [{"id": "default", "position": "top", "label": ""}]}'::jsonb, '{"sections": [{"title": "Connection", "fields": [{"key": "config.databaseType", "label": "Database Type", "type": "select", "required": true, "options": [{"value": "postgresql", "label": "PostgreSQL"}, {"value": "mssql", "label": "MS SQL Server"}, {"value": "mysql", "label": "MySQL / MariaDB"}, {"value": "mongodb", "label": "MongoDB"}, {"value": "sqlite", "label": "SQLite"}, {"value": "oracle", "label": "Oracle"}], "defaultValue": "postgresql"}, {"key": "config.connectionId", "label": "Connection ID", "type": "text", "required": true, "description": "Identifier of the registered database connection to use."}]}, {"title": "Query", "fields": [{"key": "config.query", "label": "SQL Query", "type": "code", "language": "sql", "required": true, "rows": 8, "description": "SQL to execute. Use :param_name placeholders for bound parameters."}, {"key": "config.timeoutSeconds", "label": "Timeout (seconds)", "type": "number", "defaultValue": 30}]}, {"title": "Parameters", "fields": [{"key": "config.parameters", "label": "Bound Parameters", "type": "key_value_list", "description": "Key-value pairs bound to :param_name placeholders in the query. Values support {{variable.path}} expressions."}]}, {"title": "Output Structure", "fields": [{"key": "config.outputStructure", "label": "Fields", "type": "key_value_list", "addLabel": "Add Field", "placeholderKey": "fieldName", "placeholderVal": "Value or {{path}}", "showType": true, "description": "Map named output fields from this node''s response. Reference downstream as {{nodes.NODE_NAME.output.FIELD_NAME}}."}]}, {"title": "Variable Updates", "fields": [{"key": "config.variableUpdates", "label": "Updates", "type": "state_update_list", "description": "Update workflow variables when this node completes."}]}, {"type": "accordion", "label": "Advanced", "defaultOpen": false, "fields": [{"key": "config.rowSchema", "label": "Row Schema (JSON Schema)", "type": "json", "description": "JSON Schema describing the expected shape of each result row (used for validation)."}]}]}'::jsonb, '{"type": "object", "properties": {"rows": {"type": "array", "description": "Array of result rows (SELECT)."}, "rowCount": {"type": "number", "description": "Number of rows affected or returned."}}}'::jsonb, '{"rules": ["required_name"]}'::jsonb, 17, true)
ON CONFLICT (type) DO UPDATE SET
    label = EXCLUDED.label,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color,
    description = EXCLUDED.description,
    default_name_prefix = EXCLUDED.default_name_prefix,
    default_config = EXCLUDED.default_config,
    handles = EXCLUDED.handles,
    form_schema = EXCLUDED.form_schema,
    output_schema = EXCLUDED.output_schema,
    validation_schema = EXCLUDED.validation_schema,
    sort_order = EXCLUDED.sort_order,
    is_active = true;

INSERT INTO schema_migrations (version) VALUES ('005_seed_node_types')
    ON CONFLICT (version) DO UPDATE SET applied_at = now();
