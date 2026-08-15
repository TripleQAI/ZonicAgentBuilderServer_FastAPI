# Zonic Agent Builder — Server (FastAPI)

Backend for the InSite Agent Workflow Builder. Owns import/export, validation,
relationship derivation and semantic embedding.

**It does not own data access.** There is no ORM, no database driver, no
connection pool and no DSN in this repository. Every read and write goes to the
[pgfoundation](../../ZonicPostgresqlServer_FastAPI) gateway over HTTP, using its
governed surface: `view` for reads, `procedure` for writes. No SQL text ever
leaves this service.

See [MIGRATION_PLAN.md](../MIGRATION_PLAN.md) §7–§8 for the reasoning.

---

## Architecture at a glance

```
api/v1 routers  ->  services  ->  repositories  ->  PgGateway (port)
   (thin)          (decisions)     (RelationSpec)     |
                                                      +-- HttpPgGateway  -> pgfoundation :8600 -> PostgreSQL
                                                      +-- FakeGateway    -> in-memory (tests)
```

Only `app/gateway/` knows pgfoundation exists. Everything above it depends on
the `PgGateway` protocol, which is why the entire unit suite runs with no
database and no gateway process.

| Layer | Rule |
|---|---|
| `api/` | Parse, delegate, return. No business logic. |
| `services/` | All decisions: relationship derivation, warnings, validation, the `raw_json` overlay. |
| `repositories/` | Named views and procedures only, driven by `domain/tables.py`. |
| `gateway/` | The only module that speaks pgfoundation's wire format. |
| `db/*.sql` | Views, procedures and indexes over the existing tables. Applied out-of-band with `psql`. |

Two hygiene rules are enforced by tests, not convention
(`tests/unit/test_hygiene.py`): **no SQL text anywhere under `app/`**, and **no
database driver import**.

---

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
| `001_extensions.sql` | `pgcrypto`, and the `agent_builder` schema |
| `002_schema.sql` | Base tables — a **no-op** on a Django-created database; present so a clean install works |
| `003_functions_triggers.sql` | `updated_at` triggers Django never created |
| `004_indexes.sql` | The eleven indexes the access paths need |
| `005_adapt_existing_schema.sql` | **Verifies** the tables have the expected columns and fails loudly if not; adds column defaults, a unique index on tool name, and the `tool_type` CHECK |
| `009_api_views.sql` | The read surface |
| `010_api_procedures.sql` | The write surface |
| `011_grants.sql` | Least privilege; run separately with your role name |

Every file is idempotent, so re-running picks up changed views and procedures.
`005` matters most: `CREATE TABLE IF NOT EXISTS` silently skips a table that
already exists, so a column mismatch would otherwise surface much later as a
confusing runtime error.

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
| GET | `/node-types` | Node registry (DB first, JSON fallback) |
| GET | `/tools` | Tool catalogue |
| POST | `/workflows/validate` | Validate a workflow document |
| POST | `/workflows/run-mock` | Deprecated stub, kept for parity |

### Error envelope

```json
{ "error": "...", "code": "not_found", "traceId": "..." }
```

`code` is one of `not_found`, `invalid_request`, `conflict`, `upstream_failure`,
`data_unavailable`, `internal`. Gateway failures are translated at the boundary,
so pgfoundation's error types never reach a client.

---

## The node registry

17 node types live as JSON under `app/resources/node_types/`, with shared
sections in `app/resources/fragments/` referenced as `{"$ref": "..."}`. Adding a
node type is one JSON file — no code change.

They were transcribed mechanically from the source project, and the
transcription is verifiable:

```powershell
python scripts/gen_registry_resources.py --check   # resources match the source registry
```

Three more things are data rather than code, all under `app/resources`:

| Resource | Replaces | Served at |
|---|---|---|
| `validation_rules.json` | the validator's `if/elif` ladder — five primitives evaluate it | — |
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
pytest                    # 113 tests, no database required
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
- What *is* verified about the SQL: all 107 statements and all 10 routine bodies
  parse with `libpg_query`, PostgreSQL's own parser. That catches syntax, not
  semantics — it does not prove a column exists or a procedure does the right
  thing. `005_adapt_existing_schema.sql` is the run-time check for the former.
- Frontend parity work (P4–P8) is tracked in the plan.
