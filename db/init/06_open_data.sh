#!/usr/bin/env bash
# Government open-data snapshots (import-open-data D4), loaded in both datasets: they describe
# districts, not cafes. Regenerate the CSVs with backend/scripts/prepare_open_data.py.
# The snapshots live in open_data/ because Postgres runs every file directly in /docker-entrypoint-initdb.d.
# Sourced or executed alike: no exit, and BASH_SOURCE (not $0) finds the snapshots.
set -euo pipefail

OPEN_DATA="$(dirname "${BASH_SOURCE[0]}")/open_data"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
\copy district_population (city, district, population, area_km2, as_of) FROM '${OPEN_DATA}/district_population.csv' WITH (FORMAT csv, HEADER true)
\copy universities (code, name, ownership, level, city, district) FROM '${OPEN_DATA}/universities.csv' WITH (FORMAT csv, HEADER true)
GRANT SELECT ON district_population, universities TO genbi_reader;
SQL
