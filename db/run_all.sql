-- run_all.sql — apply the whole schema, in order.
--
--   psql "$AGENTBUILDER_DSN" -v ON_ERROR_STOP=1 -f db/run_all.sql
--
-- Every file is idempotent, so re-running this is a no-op that also picks up
-- any changed view or procedure.
--
-- 011_grants.sql is NOT included: it needs the name of the role your gateway
-- connects as. Run it separately once, after creating that role:
--
--   psql "$AGENTBUILDER_DSN" -v ON_ERROR_STOP=1 -v pgf_role=agentbuilder_app \
--        -f db/011_grants.sql

\echo '== 001 extensions'
\i 001_extensions.sql
\echo '== 002 schema'
\i 002_schema.sql
\echo '== 003 functions and triggers'
\i 003_functions_triggers.sql
\echo '== 004 indexes'
\i 004_indexes.sql
\echo '== 005 seed node types'
\i 005_seed_node_types.sql
\echo '== 006 seed tools'
\i 006_seed_tools.sql
\echo '== 009 api views'
\i 009_api_views.sql
\echo '== 010 api procedures'
\i 010_api_procedures.sql

\echo ''
\echo 'Deployed schema versions:'
SELECT version, applied_at FROM schema_migrations ORDER BY version;
