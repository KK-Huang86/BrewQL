#!/usr/bin/env bash
# Knowledge base for RAG (rag-knowledge-base D5). Only the importer, genbi_knowledge_writer, writes it,
# and it can touch nothing else. genbi_reader may SELECT it for retrieval, but the table is not in the
# SQL guard's whitelist, so model-written SQL still cannot query it.
set -euo pipefail

: "${GENBI_KNOWLEDGE_WRITER_PASSWORD:?GENBI_KNOWLEDGE_WRITER_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v knowledge_pw="$GENBI_KNOWLEDGE_WRITER_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_documents (
    id           TEXT PRIMARY KEY,                 -- the document id in backend/knowledge/*.yaml
    kind         TEXT NOT NULL CHECK (kind IN ('schema', 'glossary', 'example')),
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    content_hash TEXT NOT NULL,                    -- unchanged hash: the importer skips the embedding
    embedding    vector(1024) NOT NULL,            -- Titan Text Embeddings V2
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- No vector index yet (D7): tens of documents, a full scan is fast.

CREATE ROLE genbi_knowledge_writer LOGIN PASSWORD :'knowledge_pw'
    NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 2;
ALTER ROLE genbi_knowledge_writer SET statement_timeout = '30s';

GRANT USAGE ON SCHEMA public TO genbi_knowledge_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_documents TO genbi_knowledge_writer;
GRANT SELECT ON knowledge_documents TO genbi_reader;
SQL
