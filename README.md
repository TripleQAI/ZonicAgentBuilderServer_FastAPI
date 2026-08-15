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
| `db/*.sql` | Schema, views, procedures. Applied out-of-band with `psql`. |

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

### 1. Create the database schema

The application never runs DDL. Apply it once with `psql`:

```powershell
$env:AGENTBUILDER_DSN = "postgresql://user:pass@localhost:5434/agentworkflowbuilder"
.\scripts\init_db.ps1                          # schema + views + procedures + seeds
.\scripts\init_db.ps1 -Role agentbuilder_app   # ...and least-privilege grants
.\scripts\init_db.ps1 -Drop                    # tear down first (test databases)
```

Every file is idempotent, so re-running picks up changed views and procedures.

### 2. Register the datasource with the gateway

`deploy/pgfoundation.agentbuilder.yaml` lives here, not in the gateway project.
Point the gateway at it:

```powershell
$env:PGF_CONFIG      = "$PWD\deploy\pgfoundation.agentbuilder.yaml"
$env:AGENTBUILDER_DSN = "postgresql://user:pass@localhost:5434/agentworkflowbuilder"
# then start pgfoundation as usual
```

Verify: `curl http://localhost:8600/v1/datasources` should list `agentbuilder`.

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
python scripts/gen_seed_sql.py --check             # seed SQL matches the resources
```

Per-node validation rules are data too, in `app/resources/validation_rules.json`,
evaluated by five primitives in `app/services/validation/rules.py`.

---

## Tests

```powershell
pytest                    # 81 tests, no database required
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
| `tests/contract/` | Our gateway DTOs against pgfoundation's committed OpenAPI snapshot |

---

## Known gaps

- **The live suite has not been run.** No PostgreSQL instance or gateway was
  available during the build, so `db/*.sql` and the `jsonb`-argument encoding
  (plan §8.10, task P1.0) are **unverified against a real server**. `FakeGateway`
  reimplements the same semantics in Python, and the two can drift until the live
  run happens. Treat that as the next task, not as covered.
- Frontend parity work (P4–P8) is tracked in the plan.
