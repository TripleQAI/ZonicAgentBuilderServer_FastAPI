-- run_all.sql — apply the whole schema, in order.
--
--   psql "$AGENTBUILDER_DSN" -v ON_ERROR_STOP=1 -f db/run_all.sql
--
-- NO psql? Run 000_preflight.sql first and read the report, then paste these
-- files into the SQL editor one at a time, in this order:
--
--     001, 002, 003, 004, 005, 009, 010
--
-- None of them uses a psql meta-command, so each pastes and runs as-is. Only
-- this file and 011 need psql (or, for 011, a `SET agentbuilder.role` first).
--
-- Everything lives in the agent_builder schema, on top of the tables the Django
-- app already created there. Every file is idempotent, so re-running is a no-op
-- that also picks up any changed view or procedure.
--
-- 005 verifies the existing tables have the columns this service needs and
-- fails loudly if they do not, which is the check `CREATE TABLE IF NOT EXISTS`
-- cannot make on its own.
--
-- There is no seed step. The registry is JSON under app/resources, and the API
-- serves it directly when node_type_definition is empty, so nothing has to be
-- written into the database for the application to work. Populate the table
-- only if you want to override the shipped registry: set
-- SEED_REGISTRY_ON_STARTUP=true once, or call sp_node_type_upsert yourself.
--
-- 011_grants.sql is NOT included: it needs the name of the role your gateway
-- connects as. Run it separately once, after creating that role:
--
--   psql "$AGENTBUILDER_DSN" -v ON_ERROR_STOP=1 -v pgf_role=agentbuilder_app \
--        -f db/011_grants.sql

\echo '== 001 extensions and schema'
\i 001_extensions.sql
\echo '== 002 base tables (no-op on a Django-created database)'
\i 002_schema.sql
\echo '== 003 functions and triggers'
\i 003_functions_triggers.sql
\echo '== 004 indexes'
\i 004_indexes.sql
\echo '== 005 verify and adapt the existing schema'
\i 005_adapt_existing_schema.sql
\echo '== 009 api views'
\i 009_api_views.sql
\echo '== 010 api procedures'
\i 010_api_procedures.sql

\echo ''
\echo 'Deployed schema versions:'
SELECT version, applied_at FROM agent_builder.schema_migrations ORDER BY version;
