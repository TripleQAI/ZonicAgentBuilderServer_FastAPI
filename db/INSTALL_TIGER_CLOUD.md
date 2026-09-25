# Installing into Tiger Cloud (SQL editor)

Applies the views, procedures, indexes and triggers on top of the six
`agentBuilder_*` tables that already exist in the `agent_builder` schema.

**Nothing here writes to a base table.** No row of your migrated data is
inserted, updated or deleted at any step.

Console → your service → **Explorer** → **SQL Editor**. Open each file from
`db/`, paste the whole contents, press **Run**.

> The editor shows only the **last** statement's result set. Every file below is
> written so that is the informative one.

---

## Step 0 — `000_preflight.sql`  ·  read only

Paste and Run. You get one row per check:

| status | meaning |
|---|---|
| `OK` | nothing to do |
| `INFO` | context, not a problem |
| `ACTION` | something will be created |
| `BLOCK` | **stop** and fix before continuing |

Read every row before going on. Expect roughly:

```
1. environment                     INFO    PostgreSQL 17.x
1. environment                     OK      gen_random_uuid() available
2. schema                          OK      agent_builder exists
3. table agentBuilder_agentworkflow        OK   present, ~N row(s)
   ... one row per table ...
4. columns                         OK      all 66 expected columns present
5. routines                        INFO    0 of 10 already exist and will be replaced
5. views                           INFO    0 of 8 already exist and will be replaced
```

**If `4. columns` says BLOCK**, it lists exactly which are missing. That means
the Django migrations were not all applied before the data was moved — apply
them, or add the columns, before continuing. Step 3 would refuse anyway.

To see the tool-name check (statement 1) on its own, select just that statement
and Run, or scroll up in the editor and run it alone.

---

## Steps 1–6 — apply, in this order

Run each file completely before starting the next. Order matters: `005` creates
the unique index and column defaults that later files and the application rely
on.

| # | File | What you should see |
|---|---|---|
| 1 | `001_extensions.sql` | `NOTICE: gen_random_uuid() is already available.` |
| 2 | `002_schema.sql` | No output. **Expected** — every `CREATE TABLE IF NOT EXISTS` skips, because your tables already exist. This file only matters on a clean database. |
| 3 | `003_functions_triggers.sql` | No output. Creates `set_updated_at()` and three triggers. |
| 4 | `004_indexes.sql` | No output. Creates 11 indexes. |
| 5 | `005_adapt_existing_schema.sql` | `NOTICE: agent_builder schema verified.` then the ALTERs. **If it raises instead, stop** — the message names the missing columns. |
| 6 | `009_api_views.sql` | No output. Creates 8 views. |
| 7 | `010_api_procedures.sql` | No output. Creates 4 functions and 6 procedures. |

`002` doing nothing is the normal result on your database, not a failure.

### Skip `011_grants.sql`

It restricts a dedicated, non-owner role. On Tiger Cloud you connect as
`tsdbadmin`, which owns the schema — `REVOKE` against an owner is a no-op, so
the file would run and achieve nothing. Apply it only if you later create a
separate role for the gateway; it will tell you if you point it at an owner.

---

## Step 7 — verify

Paste and Run. Every row should say `OK`:

```sql
SELECT '8 views'      AS expect,
       count(*)::text AS got,
       CASE WHEN count(*) = 8 THEN 'OK' ELSE 'MISSING' END AS status
FROM pg_views WHERE schemaname = 'agent_builder'
UNION ALL
SELECT '10 routines', count(*)::text,
       CASE WHEN count(*) = 10 THEN 'OK' ELSE 'MISSING' END
FROM pg_proc WHERE pronamespace = to_regnamespace('agent_builder')
UNION ALL
SELECT '11 indexes', count(*)::text,
       CASE WHEN count(*) >= 11 THEN 'OK' ELSE 'MISSING' END
FROM pg_indexes WHERE schemaname = 'agent_builder' AND indexname LIKE 'idx_%'
UNION ALL
SELECT '3 triggers', count(*)::text,
       CASE WHEN count(*) = 3 THEN 'OK' ELSE 'MISSING' END
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
WHERE c.relnamespace = to_regnamespace('agent_builder') AND NOT t.tgisinternal;
```

Then confirm the read surface returns your real data:

```sql
SELECT count(*) AS agents FROM agent_builder.v_agent_summary;
SELECT agentic_workflow_id, display_name, node_count, edge_count
FROM agent_builder.v_agent_summary ORDER BY updated_at DESC LIMIT 5;
```

And that the overlay view produces whole documents rather than nulls:

```sql
SELECT count(*) FILTER (WHERE export_json IS NULL) AS null_exports,
       count(*)                                    AS total
FROM agent_builder.v_agent_export;
```

`null_exports` must be `0`.

---

## Step 8 — point the services at it

1. **Gateway datasource.** Put the Tiger Cloud connection string in
   `AGENTBUILDER_DSN` and start pgfoundation with
   `PGF_CONFIG=<repo>/deploy/pgfoundation.agentbuilder.yaml`.
   Use the **direct** connection string, not the pooler, unless you have
   confirmed the pooler is in session mode.
   Check: `curl https://pgfoundation.dev.tripleq.ai/v1/datasources` lists `agentbuilder`.
2. **This service.** `.env` needs `PG_GATEWAY_BASE_URL`,
   `PG_GATEWAY_DATASOURCE=agentbuilder` and `PG_GATEWAY_SCHEMA=agent_builder`.
   Check: `curl http://localhost:8000/health/ready` returns `"status":"ready"`.
3. **End to end.** `curl http://localhost:8000/api/v1/agents` should list the
   workflows already in your database.

Leave `SEED_REGISTRY_ON_STARTUP=false`. The API serves the node registry from
JSON when `agentBuilder_nodetypedefinition` is empty, so seeding is optional —
and turning it on overwrites any row edited there by hand.

---

## Rolling back

`999_drop_all.sql` removes only what these steps created — views, routines,
triggers, `schema_migrations`. The `agentBuilder_*` tables and your data are
left alone; the statement that would drop them is commented out.

Indexes and column defaults from `004` and `005` are additive and are not
removed. To undo those, drop the `idx_*` indexes and
`ALTER COLUMN ... DROP DEFAULT` by hand.
