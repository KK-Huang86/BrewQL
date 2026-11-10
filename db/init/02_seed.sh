#!/usr/bin/env bash
# Demo data (DATASET=demo, the default). DATASET=real leaves the tables empty: the cafe-import
# service fills them with real cafes and simulated behaviour (import-real-cafes D1, D3).
# The seed lives in demo/ because Postgres runs every file directly in /docker-entrypoint-initdb.d.
# Sourced or executed alike: no exit, and BASH_SOURCE (not $0) finds the seed.
set -euo pipefail

if [ "${DATASET:-demo}" = "real" ]; then
    echo "DATASET=real: demo seed skipped"
else
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
         -f "$(dirname "${BASH_SOURCE[0]}")/demo/02_seed.sql"
fi
