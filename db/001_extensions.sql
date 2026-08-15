-- 001_extensions.sql — extensions and the schema this project lives in.
-- Idempotent.

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid() on PostgreSQL < 13

-- Everything this project reads or writes lives in agent_builder. The schema
-- already exists on a database created by the Django app; this is here so a
-- clean install works too.
CREATE SCHEMA IF NOT EXISTS agent_builder;
