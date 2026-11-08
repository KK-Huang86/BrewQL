#!/usr/bin/env bash
# Run every story check against a seeded database; each file raises on failure.
# Runs them all and reports each, so a red run lists every broken story at once.
#
#   PSQL="docker exec -i brewql-test-db psql -U genbi_owner -d genbi" db/checks/run.sh
#   db/checks/run.sh            # CI: plain psql with PGHOST/PGUSER/... set
set -uo pipefail

PSQL=${PSQL:-psql}
dir="$(cd "$(dirname "$0")" && pwd)"
failed=0
for f in "$dir"/[0-9]*.sql; do
  if out=$($PSQL -X -q -v ON_ERROR_STOP=1 < "$f" 2>&1); then
    echo "pass $(basename "$f")"
  else
    echo "FAIL $(basename "$f"): $(grep -m1 ERROR <<<"$out")"
    failed=1
  fi
done
exit $failed
