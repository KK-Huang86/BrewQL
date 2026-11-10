#!/usr/bin/env bash
# Demo data (DATASET=demo, the default). DATASET=real leaves the tables empty: the cafe-import
# service fills them with real cafes and simulated behaviour (import-real-cafes D1, D3).
# The seed lives in demo/ because Postgres runs every file directly in /docker-entrypoint-initdb.d.
# Sourced or executed alike: no exit, and BASH_SOURCE (not $0) finds the seed.
set -euo pipefail

case "${DATASET:-demo}" in
    demo)
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
             -f "$(dirname "${BASH_SOURCE[0]}")/demo/02_seed.sql"
        ;;
    real)
        echo "DATASET=real: demo seed skipped"
        ;;
    *)
        # A typo would otherwise seed demo into a volume named after it; failing stops init.
        echo "DATASET must be demo or real, got '${DATASET}'" >&2
        false
        ;;
esac
