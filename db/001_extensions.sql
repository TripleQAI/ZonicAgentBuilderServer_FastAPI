-- 001_extensions.sql — required extensions.
-- Idempotent. gen_random_uuid() is built in from PostgreSQL 13; pgcrypto covers older servers.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
