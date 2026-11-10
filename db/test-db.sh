#!/usr/bin/env bash
# Throwaway Postgres for integration tests, initialised by db/init like compose.
# Uses the same throwaway passwords as CI; never use for real data.
#
#   db/test-db.sh up     # start, wait for init, print the TEST_*_DATABASE_URL exports
#   db/test-db.sh down   # remove the container (data is not kept)
set -euo pipefail

NAME=brewql-test-db
PORT=${TEST_DB_PORT:-5499}
INIT_DIR="$(cd "$(dirname "$0")" && pwd)/init"
URL="postgresql://genbi_reader:ci-reader-password@127.0.0.1:${PORT}/genbi"
AUDIT_URL="postgresql://genbi_audit_writer:ci-audit-password@127.0.0.1:${PORT}/genbi"
KNOWLEDGE_URL="postgresql://genbi_knowledge_writer:ci-knowledge-password@127.0.0.1:${PORT}/genbi"
OWNER_URL="postgresql://genbi_owner:ci-owner-password@127.0.0.1:${PORT}/genbi"

case "${1:-}" in
  up)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --rm --name "$NAME" -p "127.0.0.1:${PORT}:5432" \
      -e POSTGRES_DB=genbi -e POSTGRES_USER=genbi_owner \
      -e POSTGRES_PASSWORD=ci-owner-password -e GENBI_READER_PASSWORD=ci-reader-password \
      -e GENBI_AUDIT_WRITER_PASSWORD=ci-audit-password -e GENBI_KNOWLEDGE_WRITER_PASSWORD=ci-knowledge-password \
      -v "${INIT_DIR}:/docker-entrypoint-initdb.d:ro" pgvector/pgvector:pg16 >/dev/null
    # pg_isready turns true during init too; wait for the final server start.
    for _ in $(seq 60); do
      # Process substitution: with pipefail, grep -q closing the pipe early would fail it.
      if grep -q 'PostgreSQL init process complete' <(docker logs "$NAME" 2>&1) \
        && docker exec "$NAME" pg_isready -q -h 127.0.0.1 -U genbi_owner -d genbi; then
        echo "export TEST_DATABASE_URL=${URL}"
        echo "export TEST_AUDIT_DATABASE_URL=${AUDIT_URL}"
        echo "export TEST_KNOWLEDGE_DATABASE_URL=${KNOWLEDGE_URL}"
        echo "export TEST_OWNER_DATABASE_URL=${OWNER_URL}"
        exit 0
      fi
      sleep 1
    done
    echo "test database did not become ready; see: docker logs ${NAME}" >&2
    exit 1
    ;;
  down)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    ;;
  *)
    echo "usage: $0 up|down" >&2
    exit 2
    ;;
esac
