# curl reference

Every route under `/api/v1`, plus the gateway and SQL objects each one reaches.

All responses below were captured from a running server against the real
`agent.json` / `sub_agents.json` sample (28 nodes, 54 edges, 8 sub-agents), so
the shapes are observed rather than described.

```bash
API=http://localhost:8000
GW=http://localhost:8600            # pgfoundation
DS=tsdb                             # must equal PG_GATEWAY_DATASOURCE
ID=935e5116-b512-4434-82b9-bba32de3d3f8
```

---

## Import into Postman

Postman cannot import Markdown, so this file stays the readable reference and
ships alongside two things Postman *does* import.

### 1. The collection (recommended)

**Import → Files** → `docs/postman/agent-builder.postman_collection.json`
**Import → Files** → `docs/postman/agent-builder.postman_environment.json`

Then pick **Agent Builder — local** in the environment dropdown.

27 requests in 5 folders: Health, Agents, Registry, Workflows, and a
**Data gateway** folder that talks to pgfoundation on `:8600` directly — useful
for proving the views and procedures work before the application is involved.

Two things make it usable rather than just complete:

- **Import a package** writes the returned root id into the `ID` collection
  variable, so every request below it targets the workflow you just imported.
- Several requests carry tests — readiness asserts the data path is up,
  node-types asserts all 17 are served, the 404 request asserts the error
  envelope.

Variables: `API`, `GW`, `DS`, `SCHEMA`, `ID`. Set `DS` to whatever
`GET {{GW}}/v1/datasources` returns; a mismatch is the usual cause of a 502
`unknown data source`.

The one manual step: the multipart import request cannot store file paths in an
exported collection, so select `tests/fixtures/agent.json` and
`sub_agents.json` in its **Body** tab before sending. The JSON variant next to
it needs no files.

### 2. The OpenAPI document (always current)

**Import → Link** → `http://localhost:8000/openapi.json`

Generated from the Pydantic models, so it can never be out of date — but it has
no worked example bodies, no tests, and no gateway requests. Good for checking
a schema; the collection is better for actually driving the API.

### 3. A single command

**Import → Raw text**, paste any `curl` command from this file, **Continue**.
Handy for one-off checks without importing anything.

### Keeping the collection honest

A hand-maintained collection drifts the moment a route changes.
`tests/contract/test_postman_collection.py` compares it against the app's own
OpenAPI in both directions — a request pointing at a route that no longer
exists fails, and so does a route with no request. It also checks that every
JSON body parses, that URLs only use declared variables, that the gateway
folder never reaches for the disabled raw-SQL endpoints, and that each
procedure call carries the right number of INOUT `null` placeholders.

---

> **On Windows, use `curl.exe`, not `curl`.** In PowerShell 5.1 `curl` is an
> alias for `Invoke-WebRequest`, which takes different arguments and will fail
> on every command here. Single-quoted JSON also does not survive PowerShell —
> see [PowerShell bodies](#powershell-bodies) at the end.

---

## What each route touches

The application never names a table. Reads name a view, writes call a
procedure, and the schema (`agent_builder`) is attached to every call by the
HTTP adapter.

| Route | Gateway op | SQL object |
|---|---|---|
| `GET /agents` | `view` | `v_agent_summary` |
| `GET /agents/{id}` | `view` | `v_agent_detail` |
| `PUT /agents/{id}` | `procedure` | `sp_agent_workflow_save` → `fn_agent_workflow_upsert`, `fn_agent_relationship_replace` |
| `POST /agents/import-package` | `procedure` | `sp_agent_package_import` |
| `GET /agents/{id}/relationships` | `view` ×2 | `v_agent_detail`, `v_agent_relationship_detail`, `v_package_agent` |
| `GET /agents/{id}/export` | `view` | `v_agent_export` |
| `GET /agents/{id}/export-package` | `view` ×3 | `v_agent_export`, `v_agent_relationship_detail` |
| `GET /agents/{id}/export-debug` | `view` ×4 | as above + `v_package_agent` |
| `POST /agents/{id}/snapshots` | `procedure` | `sp_workflow_snapshot_create` |
| `POST /agents/{id}/embed` | `view` + `procedure` | `v_agent_detail`, `sp_agent_embedding_store` |
| `GET /node-types` | `view` | `v_node_type_active` (falls back to JSON when empty) |
| `GET /tools` | `view` | `v_tool_active` (falls back to JSON when empty) |
| `GET /option-sets` | — | none; served from `app/resources/option_sets.json` |
| `GET /node-semantics` | — | none; served from `app/resources/node_semantics.json` |
| `GET /mcp-config-schema` | — | none; served from `app/resources/mcp_config.json` |
| `POST /workflows/validate` | — | none; pure computation |
| `POST /workflows/run-mock` | — | none; deprecated stub |

---

## Health

```bash
curl -s $API/health
# {"status":"ok","gateway":"http://localhost:8600","datasource":"tsdb"}

curl -s $API/health/ready        # 503 when the gateway is unreachable
# {"status":"ready","gateway":"http://localhost:8600","datasource":"tsdb"}
```

`/health` is liveness and never touches the gateway. `/health/ready` calls the
gateway's own `/ready`, so it is the one to probe.

---

## Agents

### List

```bash
curl -s $API/api/v1/agents
```
```json
{"agents":[{"agenticWorkflowId":"935e5116-…","name":"intelligent-buying-orchestrator",
  "displayName":"Intelligent Buying Orchestrator","isRoot":true,
  "nodeCount":28,"edgeCount":54,"environment":"","updatedAt":"2026-08-16T02:10:14Z"}]}
```

### Import a package

Multipart — what the UI sends:

```bash
curl -s -X POST $API/api/v1/agents/import-package \
  -F "agent_file=@tests/fixtures/agent.json" \
  -F "sub_agents_file=@tests/fixtures/sub_agents.json"
```
```json
{"root_agent_id":"935e5116-…","sub_agent_ids":["04d070d9-…", "…"],
 "relationship_count":9,
 "warnings":["Node 'exec_category_agnostic' references agenticWorkflowId '025421e9-…' which is not in sub_agents"],
 "parent_package_id":"…"}
```

Or as JSON, which is easier to script:

```bash
curl -s -X POST $API/api/v1/agents/import-package \
  -H 'content-type: application/json' \
  -d '{"agent_data":{"agenticWorkflowId":"11111111-2222-3333-4444-555555555555",
                     "name":"demo","displayName":"Demo",
                     "nodes":[{"id":"n1","type":"start","name":"Start","config":{}}],
                     "edges":[]},
       "sub_agents_data":null}'
```

Those response keys are `snake_case` on purpose — the Django endpoint returned
them that way and the UI reads them directly.

The whole package lands in **one** `CALL`, so a failed import leaves nothing
behind.

### Read one

```bash
curl -s $API/api/v1/agents/$ID
```

Returns the agent's own document — `raw_json` with the first-class fields
overlaid. Unknown keys (`createdBy`, `originalBpc`, `freezeRelease`) survive.

### Save

```bash
curl -s -X PUT $API/api/v1/agents/$ID \
  -H 'content-type: application/json' \
  -d '{"displayName":"Renamed via curl"}'
```
```json
{"status":"saved","agenticWorkflowId":"935e5116-…",
 "relationshipCount":9,"nodeCount":28,"edgeCount":54}
```

**Partial saves are patches.** Keys you omit keep their stored value, and
omitting `nodes` leaves the relationship edges alone — the canvas has not
changed, so neither have they. Sending `"nodes": []` is a real edit and *does*
clear them. The two are deliberately different.

A save is an upsert: PUT an id that does not exist and it is created as a root.

### Relationships

```bash
curl -s $API/api/v1/agents/$ID/relationships
```
```json
{"rootAgentId":"935e5116-…","rootAgentName":"intelligent-buying-orchestrator",
 "resolvedCount":8,"unresolvedCount":1,
 "resolved":[{"sourceNodeId":"l2mtx56","sourceNodeName":"…","isResolved":true,
              "childAgent":{"displayName":"v3 Category Specific Questionnaire",
                            "nodeCount":11,"edgeCount":15}}],
 "unresolved":[{"childAgenticWorkflowId":"025421e9-…",
                "validationMessage":"Child workflow 025421e9-… not found in sub_agents"}],
 "unreferencedSubAgents":[]}
```

One read, child details included. The Django version issued an extra query per
child.

### Export

```bash
curl -s $API/api/v1/agents/$ID/export          > agent.json
curl -s $API/api/v1/agents/$ID/export-package  > package.json   # agent + sub_agents + relationshipMap
curl -s $API/api/v1/agents/$ID/export-debug    > debug.json     # package + warnings
```

Observed on the sample: `export-package` → 8 `sub_agents`, 9 `relationshipMap`
entries; `export-debug` → 8 warnings.

### Snapshot

```bash
curl -s -X POST $API/api/v1/agents/$ID/snapshots \
  -H 'content-type: application/json' -d '{"comment":"before edit"}'
```
```json
{"snapshotId":"fb2debfa-…","agenticWorkflowId":"935e5116-…",
 "createdAt":"2026-08-16T02:10:14.616669Z"}
```

Built from the persisted row, not the request — a snapshot always reflects what
is stored.

### Embed

```bash
curl -s -X POST $API/api/v1/agents/$ID/embed
```

`400` when semantic search is off for that workflow, which is the default:

```json
{"error":"Semantic search is not enabled for this workflow.","code":"invalid_request","traceId":"…"}
```

Enable it first, then embed:

```bash
curl -s -X PUT $API/api/v1/agents/$ID -H 'content-type: application/json' \
  -d '{"semanticSearchEnabled":true,"semanticDomain":"energy",
       "semanticKeywords":"energy, meters","semanticUseCases":"Compare usage across sites"}'
curl -s -X POST $API/api/v1/agents/$ID/embed
# {"status":"indexed","agenticWorkflowId":"…","dimensions":1024,"textLength":142}
```

Needs `EMBEDDING_PROVIDER=bedrock` and working AWS credentials; set
`EMBEDDING_PROVIDER=fake` to exercise the path without calling Bedrock.

---

## Registry

```bash
curl -s $API/api/v1/node-types    # {"nodeTypes":[ …17 items… ]}
curl -s $API/api/v1/tools         # {"tools":[ …5 items… ]}
curl -s $API/api/v1/option-sets
# {"mappingTypes":6,"stateOps":7,"schemaTypes":6,
#  "messageRoles":3,"invocationTypes":3,"semanticDomains":3}   (lengths shown)

curl -s $API/api/v1/node-semantics
# {"childReference":{"workflow":"config.agenticWorkflowId"},
#  "handoffTargets":{"agent":"config.handoffTarget"},
#  "branches":{"rule":{"path":"config.rules","idField":"ruleId"}}}

curl -s $API/api/v1/mcp-config-schema
# {"server":{…9 fields…},"serverDefaults":{…},
#  "toolKinds":[{"value":"database",…},{"value":"api",…},{"value":"function",…}],
#  "parameterRow":{…},"cacheKeyConfig":{…}}
```

`mcp-config-schema` drives the MCP tool configurator end to end — the fields,
which of them appear when, their defaults and what is required. Adding a field
to a tool kind is an edit to `app/resources/mcp_config.json`, with no frontend
change and no new endpoint.

`node-semantics` is what lets the canvas draw the right handles: a Rule node
renders one output per configured branch and an Agent node one per handoff
target. Without it those edges have nowhere to attach and silently disappear.

`node-types` and `tools` prefer the database and fall back to the JSON
resources when the table is empty — so they work before any seeding.

---

## Workflows

```bash
curl -s -X POST $API/api/v1/workflows/validate \
  -H 'content-type: application/json' \
  -d '{"agenticWorkflowId":"11111111-2222-3333-4444-555555555555","name":"demo",
       "nodes":[{"id":"n1","type":"start","name":"Start","config":{}}],"edges":[]}'
# {"valid":true,"errors":[],"warnings":[],"node_count":1,"edge_count":0}
```

`node_count` / `edge_count` are snake_case — the UI's validation panel reads
those names.

Validating the real sample reports one error and one warning, both genuine:

```
E: Tool node 'getdecisionpointsv2': toolName is required
W: Output node 'output': no output mappings defined
```

```bash
curl -s -X POST $API/api/v1/workflows/run-mock \
  -H 'content-type: application/json' \
  -d '{"nodes":[{"id":"n1","type":"start","name":"Start"}]}'
# {"status":"mock_completed","message":"Mock execution completed. …","nodeCount":1,
#  "trace":[{"nodeId":"n1","nodeType":"start","nodeName":"Start","status":"mock_executed"}]}
```

Deprecated, kept for parity. The real mock engine is client-side.

---

## Errors

One envelope for every failure:

```bash
curl -s $API/api/v1/agents/00000000-0000-0000-0000-000000000000
# {"error":"Agent not found","code":"not_found","traceId":"e2a37ed918ce4ed896ec5ea4f148aed0"}
```

`code` ∈ `not_found` · `invalid_request` · `conflict` · `upstream_failure` ·
`data_unavailable` · `internal`. `traceId` is echoed in the `X-Request-Id`
header and forwarded to the gateway, so one identifier follows a request
through all three services.

---

## Talking to the gateway directly

Useful for testing the data layer before the application is involved — it
proves the views and procedures work.

```bash
curl -s $GW/v1/datasources
# {"datasources":["tsdb"]}     ← must contain $DS
```

Read a view:

```bash
curl -s -X POST $GW/v1/datasources/$DS/view \
  -H 'content-type: application/json' \
  -d '{"name":"v_agent_summary","schema":"agent_builder",
       "order_by":[{"column":"updated_at","descending":true}],"limit":5}'
# {"rows":[…],"row_count":5,"elapsed_ms":3.1}
```

Confirm the overlay view returns whole documents:

```bash
curl -s -X POST $GW/v1/datasources/$DS/view \
  -H 'content-type: application/json' \
  -d '{"name":"v_agent_export","schema":"agent_builder",
       "columns":["agentic_workflow_id"],"limit":1}'
```

Call a procedure. **`jsonb` arguments go as JSON text**, and the trailing
`null`s are the INOUT placeholders the gateway's `CALL` contract requires:

```bash
curl -s -X POST $GW/v1/datasources/$DS/procedure \
  -H 'content-type: application/json' \
  -d '{"name":"sp_node_type_upsert","schema":"agent_builder",
       "args":["[{\"type\":\"demo\",\"label\":\"Demo\"}]", null]}'
# {"rows":[{"o_count":1}],"row_count":1,"elapsed_ms":8.4}
```

Placeholder counts, from `app/domain/tables.py`:

| Procedure | Input args | Trailing `null`s |
|---|---|---|
| `sp_agent_workflow_save` | agent, relationships, message-format | 3 |
| `sp_agent_package_import` | root, sub_agents, relationships, message-format | 3 |
| `sp_workflow_snapshot_create` | uuid, comment | 2 |
| `sp_agent_embedding_store` | uuid, vector, text | 1 |
| `sp_node_type_upsert` | definitions | 1 |
| `sp_tool_upsert` | definitions | 1 |

`sp_agent_workflow_save` accepts SQL `null` for relationships, meaning "leave
the edges alone". That is not the same as the string `"null"`, which is JSON
null and would be treated as a value.

---

## PowerShell bodies

Single quotes and `@` do not behave the same. Use a here-string and `curl.exe`:

```powershell
$body = @'
{"displayName":"Renamed via PowerShell"}
'@
curl.exe -s -X PUT "http://localhost:8000/api/v1/agents/$ID" `
  -H "content-type: application/json" -d $body
```

Or skip curl entirely:

```powershell
Invoke-RestMethod -Method Put -Uri "http://localhost:8000/api/v1/agents/$ID" `
  -ContentType 'application/json' `
  -Body (@{ displayName = 'Renamed' } | ConvertTo-Json)
```

For file upload:

```powershell
curl.exe -s -X POST "http://localhost:8000/api/v1/agents/import-package" `
  -F "agent_file=@tests/fixtures/agent.json" `
  -F "sub_agents_file=@tests/fixtures/sub_agents.json"
```
