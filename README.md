# Zonic Agent Builder — Server (FastAPI)

Backend for the TripleQ Agent Workflow Builder. Owns import/export, validation,
relationship derivation and semantic embedding.

**It does not own data access.** There is no ORM, no database driver, no
connection pool and no DSN in this repository. Every read and write goes to the
[pgfoundation](https://github.com/TripleQAI/ZonicPostgresqlServer_FastAPI) gateway over HTTP, using its
governed surface: `view` for reads, `procedure` for writes. No SQL text ever
leaves this service.

The reasoning is in the migration plan (§7–§8), an internal document that is
not part of this repository; the design is summarised under
[Technical design](#technical-design).

---

## Nebius x NVIDIA Global AI Hackathon

This repository is part of the Zonic agent platform, our entry in the Nebius x NVIDIA Global AI Hackathon (Best Apps and Agents track). The platform's agents run on NVIDIA Nemotron models served by Nebius Token Factory. How that is wired, and which model does what, is in the runtime's README: [NVIDIA Nemotron on Nebius Token Factory](https://github.com/TripleQAI/ZonicAgentRuntimeBackend_Python_LangGraph#nvidia-nemotron-on-nebius-token-factory).

**This repository's part:** It serves the model options the builder shows, the Nemotron codes included ([`app/resources/fragments/options.models.json`](app/resources/fragments/options.models.json)). It also validates and stores the workflows the runtime runs.

**Live demo:** the chat at https://dev.tripleq.ai/agent-runtime-lg and the agent builder at https://dev.tripleq.ai/agent-visual-builder-lg/workflows. Both sign in with Amazon Cognito; the test accounts are in the hackathon submission's testing instructions.

| Repository | Role |
|---|---|
| [ZonicAgentBuilderUI_NextJS](https://github.com/TripleQAI/ZonicAgentBuilderUI_NextJS) | The visual builder: design a workflow and pick a Nemotron model for each node |
| **ZonicAgentBuilderServer_FastAPI** (this repository) | The builder's API: validation, import and export, the node registry and model options |
| [ZonicAgentRuntimeBackend_Python_LangGraph](https://github.com/TripleQAI/ZonicAgentRuntimeBackend_Python_LangGraph) | Runs the workflows on LangGraph and calls Nemotron through Token Factory |
| [ZonicAgentRuntimeUI_NextJS_For_LangGraph](https://github.com/TripleQAI/ZonicAgentRuntimeUI_NextJS_For_LangGraph) | The chat app people use the agents in |
| [ZonicMCPServer_FastAPI](https://github.com/TripleQAI/ZonicMCPServer_FastAPI) | The agents' tools over open data |
| [ZonicPostgresqlServer_FastAPI](https://github.com/TripleQAI/ZonicPostgresqlServer_FastAPI) | The PostgreSQL gateway every service stores data through (Neon) |

## Technical design

The full technical design is in [docs/technical-design.md](docs/technical-design.md):

- [Architecture](docs/technical-design.md#architecture)
- [Domain model](docs/technical-design.md#domain-model)
- [The node registry in the UI](docs/technical-design.md#the-node-registry-in-the-ui)
- [Key flows](docs/technical-design.md#key-flows)
- [Validation and errors](docs/technical-design.md#validation-and-errors)
- [Security](docs/technical-design.md#security)
- [Configuration and deployment](docs/technical-design.md#configuration-and-deployment)
- [Testing](docs/technical-design.md#testing)
- [Key design decisions](docs/technical-design.md#key-design-decisions)

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

### 1. Apply the database objects

**The tables already exist.** This service runs on top of the schema the Django
app created: schema `agent_builder`, tables named `agentBuilder_<model>` —
`agentBuilder_agentworkflow`, `agentBuilder_agentrelationship` and four more.
Those names are mixed case, so they are double-quoted everywhere; that quoting
lives only in `db/*.sql`, because the application names views and procedures,
never a table.

`db/` adds the read and write surface on top of them. The application never runs
DDL — apply it once with `psql`:

```powershell
$env:AGENTBUILDER_DSN = "postgresql://user:pass@host:5432/dbname"
.\scripts\init_db.ps1                          # views + procedures + indexes + seeds
.\scripts\init_db.ps1 -Role agentbuilder_app   # ...and least-privilege grants
.\scripts\init_db.ps1 -Drop                    # remove OUR objects (tables are left alone)
```

| File | What it does |
|---|---|
| `000_preflight.sql` | **Read only.** Run this first — reports server version, which tables exist and roughly how many rows they hold, any missing column, anything that would block the install, and what a re-run would replace |
| `001_extensions.sql` | The `agent_builder` schema, and a check that `gen_random_uuid()` is available |
| `002_schema.sql` | Base tables — a **no-op** on a Django-created database; present so a clean install works |
| `003_functions_triggers.sql` | `updated_at` triggers Django never created |
| `004_indexes.sql` | The eleven indexes the access paths need |
| `005_adapt_existing_schema.sql` | **Verifies** 28 expected columns and fails loudly if any is missing; adds column defaults, a unique index on tool name, and the `tool_type` CHECK |
| `009_api_views.sql` | The read surface |
| `010_api_procedures.sql` | The write surface |
| `011_grants.sql` | Least privilege. Optional — skip it when the gateway connects as the database owner |

### Without psql — the Tiger Cloud SQL editor

Only `run_all.sql` and `011` use psql meta-commands. Run `000_preflight.sql`,
read the report, then paste these in order:

```
001 → 002 → 003 → 004 → 005 → 009 → 010
```

For `011`, run `SET agentbuilder.role = 'your_role';` first, then paste the rest.

Every file is idempotent, so re-running picks up changed views and procedures.
`005` matters most: `CREATE TABLE IF NOT EXISTS` silently skips a table that
already exists, so a column mismatch would otherwise surface much later as a
confusing runtime error.

Nothing here writes to a base table, so it is safe to run against a database
that already holds migrated data. The views also `COALESCE` every jsonb column
they concatenate — `NULL || anything` is `NULL` in jsonb, so one null
`raw_json` would otherwise blank a whole exported document rather than degrade
a single field.

Django applies field defaults in Python, so its tables have none. The procedures
therefore supply `id`, `created_at` and `updated_at` explicitly and work with or
without `005` — but `005` adds the defaults anyway, so a hand-written `INSERT`
behaves too.

### 2. Register the datasource with the gateway

`deploy/pgfoundation.agentbuilder.yaml` lives here, not in the gateway project.
Point the gateway at it:

```powershell
$env:PGF_CONFIG      = "$PWD\deploy\pgfoundation.agentbuilder.yaml"
$env:AGENTBUILDER_DSN = "postgresql://user:pass@localhost:5434/agentworkflowbuilder"
# then start pgfoundation as usual
```

Verify: `curl http://localhost:8600/v1/datasources` should list `agentbuilder`.

The schema (`agent_builder`) is sent on every governed call via
`PG_GATEWAY_SCHEMA`, so nothing depends on the connection's `search_path`.

### 3. Run

```powershell
uvicorn app.main:app --reload --port 8000
```

- OpenAPI: http://localhost:8000/docs
- Liveness: `GET /health` · Readiness (checks the gateway): `GET /health/ready`

---

## API

All routes are under `/api/v1`. Shapes match the Django surface they replace.

| Method | Path | Purpose |
|---|---|---|
| GET | `/agents` | List workflows with node/edge counts |
| POST | `/agents/import-package` | Import `agent.json` (+ optional `sub_agents.json`); multipart or JSON |
| GET | `/agents/{id}` | One workflow, `raw_json` overlaid |
| PUT | `/agents/{id}` | Upsert. Agent + chip + relationships, one transaction |
| GET | `/agents/{id}/relationships` | Relationship map, one read |
| GET | `/agents/{id}/export` | Export one agent |
| GET | `/agents/{id}/export-package` | Agent + resolved children + relationship map |
| GET | `/agents/{id}/export-debug` | Package + unresolved/unreferenced warnings |
| POST | `/agents/{id}/snapshots` | Snapshot the persisted state |
| POST | `/agents/{id}/embed` | Generate and store the semantic vector |
| GET | `/me` | The signed-in user (`sub`, `email`) |
| GET | `/node-types` | Node registry (DB first, JSON fallback) |
| GET | `/node-semantics` | Structural roles per node type |
| GET | `/mcp-config-schema` | Form schema for the MCP tool configurator |
| GET | `/tools` | Tool catalogue |
| POST | `/workflows/validate` | Validate a workflow document |
| POST | `/workflows/run-mock` | Deprecated stub, kept for parity |
| GET | `/option-sets` | Shared select-option lists |

Worked examples for every route, with the gateway call and SQL object each one
reaches, are in [docs/curl-reference.md](docs/curl-reference.md). For Postman,
import [docs/postman/](docs/postman/) — 27 requests across the API and the
gateway, with an environment file and a `{{ID}}` variable that the import
request fills in for you.

### Error envelope

```json
{ "error": "...", "code": "not_found", "traceId": "..." }
```

`code` is one of `not_found`, `invalid_request`, `unauthorized`, `conflict`,
`upstream_failure`, `data_unavailable`, `auth_not_configured`, `internal`. Gateway failures are translated at the boundary,
so pgfoundation's error types never reach a client.

---

## The node registry

18 node types live as JSON under `app/resources/node_types/`, with shared
sections in `app/resources/fragments/` referenced as `{"$ref": "..."}`. Adding a
node type is one JSON file — no code change.

They were transcribed mechanically from the source project, and the
transcription is verifiable:

```powershell
python scripts/gen_registry_resources.py --source <path>\node_registry.py --check
```

Each node type's `icon`, `color` and `sortOrder` have since been restyled to
match the Strands Visual Builder, so `--check` reports those keys as drift.

Three more things are data rather than code, all under `app/resources`:

| Resource | Replaces | Served at |
|---|---|---|
| `validation_rules.json` | the validator's `if/elif` ladder — twelve primitives evaluate it | — |
| `node_semantics.json` | `if node_type == "workflow" / elif "agent"` in the resolver, and `== "rule"` in the validator | — |
| `option_sets.json` | six option lists the source repeated across `node_registry.py`, `dynamic_fields.js` and the page template | `GET /api/v1/option-sets` |

**The database is never seeded automatically.** `/node-types` serves the JSON
registry whenever `node_type_definition` is empty, so an unseeded table is a
working configuration, not a broken one — the same arrangement the Django app
had, where `manage.py seed_node_registry` was an optional command. Set
`SEED_REGISTRY_ON_STARTUP=true` only to push the registry into the database for
other readers; be aware it overwrites rows edited there by hand.

---

## Tests

```powershell
pytest                    # 147 tests, no database required
pytest -m live            # add the live gateway suite (needs a real gateway + DB)
ruff check app tests scripts
mypy app
```

| Suite | What it covers |
|---|---|
| `tests/integration/test_parity.py` | The 14 ported Django cases, numbered to match, plus the real 28-node sample package |
| `tests/unit/test_validation_engine.py` | Every validator check and every rule primitive |
| `tests/unit/test_gateway_layer.py` | Payload construction, the ACL status map, retry policy, port conformance |
| `tests/unit/test_registry_loader.py` | Fragment resolution, cycle detection, output shape |
| `tests/unit/test_hygiene.py` | No SQL in `app/`, no driver imports, no credentials, layer direction |
| `tests/unit/test_schema_qualification.py` | Every call sends the schema; every spec has a matching view/procedure in `db/`; Django table names stay quoted |
| `tests/unit/test_no_hardcoding.py` | No node-type literal compared in a service (AST-checked); no option list declared in the UI; resources reference only real node types |
| `tests/contract/` | Our gateway DTOs against pgfoundation's committed OpenAPI snapshot |

---

## Known gaps

- **The live suite has not been run.** No PostgreSQL instance or gateway was
  available during the build, so the `jsonb`-argument encoding (plan §8.10, task
  P1.0) is **unverified against a real server**. `FakeGateway` reimplements the
  same semantics in Python, and the two can drift until the live run happens.
  Treat that as the next task, not as covered.
- What *is* verified about the SQL: all 84 statements and 13 of the 14 plpgsql
  bodies parse with `libpg_query`, PostgreSQL's own parser. The exception is
  `set_updated_at`, where libpg_query's JSON serializer emits malformed output
  for any `RETURNS trigger` function; the same statements parse cleanly when
  `NEW` is an ordinary record, so it is a tool limitation, not a defect.
  Parsing catches syntax, not semantics — it does not prove a column exists or
  that a procedure does the right thing. `000_preflight.sql` and
  `005_adapt_existing_schema.sql` are the run-time checks for the former.
- Frontend parity work (P4–P8) is tracked in the plan.

## License

Licensed under the Apache License 2.0; see [LICENSE](LICENSE).
