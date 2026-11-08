#!/usr/bin/env bash
# Guardrail layer 1: the API connects as genbi_reader, which may only SELECT.
# Even if a DELETE slipped past the SQL guard, Postgres would refuse it.
set -euo pipefail

: "${GENBI_READER_PASSWORD:?GENBI_READER_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v reader_pw="$GENBI_READER_PASSWORD" <<'SQL'
CREATE ROLE genbi_reader LOGIN PASSWORD :'reader_pw'
    NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 20;
ALTER ROLE genbi_reader SET default_transaction_read_only = on;
ALTER ROLE genbi_reader SET statement_timeout = '5s';

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO genbi_reader;
GRANT SELECT ON cafes, users, search_logs, v_daily_activity TO genbi_reader;
SQL
