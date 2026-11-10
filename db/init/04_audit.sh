#!/usr/bin/env bash
# Audit trail for /api/ask (record-audit-log D1, D2). The API appends through genbi_audit_writer,
# which can INSERT and SELECT this one table and nothing else: no UPDATE, DELETE or TRUNCATE, so
# a compromised API cannot rewrite history. genbi_reader gets no grant on it, so SQL that slipped
# past the guard still cannot see other visitors' questions.
set -euo pipefail

: "${GENBI_AUDIT_WRITER_PASSWORD:?GENBI_AUDIT_WRITER_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v audit_pw="$GENBI_AUDIT_WRITER_PASSWORD" <<'SQL'
CREATE TABLE ask_audit (
    request_id         UUID PRIMARY KEY,           -- one per request; re-sends are ignored
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    visitor            TEXT,                       -- HMAC of the source IP, never the IP itself
    question           TEXT NOT NULL,
    sql                TEXT,                       -- last attempt: executed, or rejected by the guard
    failed_attempts    JSONB NOT NULL DEFAULT '[]', -- earlier tries: [{error_kind, reason, sql}]
    status             TEXT NOT NULL CHECK (status IN ('ok', 'clarify', 'refused', 'error')),
    refusal_source     TEXT,
    error_kind         TEXT,
    guardrail_reasons  TEXT[] NOT NULL DEFAULT '{}',
    model_id           TEXT,
    input_tokens       INTEGER NOT NULL DEFAULT 0,
    output_tokens      INTEGER NOT NULL DEFAULT 0,
    guardrail_units    INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(12, 8),             -- NULL: a price was unknown, not zero
    elapsed_ms         INTEGER,
    row_count          INTEGER                     -- only when answered; results are never stored
);
CREATE INDEX ask_audit_created_at ON ask_audit (created_at DESC);

CREATE ROLE genbi_audit_writer LOGIN PASSWORD :'audit_pw'
    NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 5;
ALTER ROLE genbi_audit_writer SET statement_timeout = '2s';

GRANT USAGE ON SCHEMA public TO genbi_audit_writer;
GRANT INSERT, SELECT ON ask_audit TO genbi_audit_writer;
SQL
