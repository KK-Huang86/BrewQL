#!/usr/bin/env bash
# Demo cafe coordinates (cafe-transit-distance D3), after 06_open_data.sh loads the stations.
# Each demo cafe sits 0-250 m from a YouBike station in its own district. The station, bearing
# and distance come from md5(place_id), never random(): 02_seed.sql shares one setseed stream,
# and drawing from it would change every simulated row and evaluation answer.
# DATASET=real keeps the export's coordinates. Sourced or executed alike: no exit.
set -euo pipefail

case "${DATASET:-demo}" in
    demo)
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
WITH draws AS (
    -- Three independent 28-bit numbers per cafe from its md5.
    SELECT c.id, c.city, c.district,
           ('x' || substr(md5(c.place_id), 1, 7))::bit(28)::int AS pick,
           ('x' || substr(md5(c.place_id), 8, 7))::bit(28)::int / 268435456.0 AS turn,
           ('x' || substr(md5(c.place_id), 15, 7))::bit(28)::int / 268435456.0 AS reach
    FROM cafes c
),
anchors AS (
    SELECT city, district, lat, lng,
           row_number() OVER (PARTITION BY city, district ORDER BY station_no) - 1 AS i,
           count(*) OVER (PARTITION BY city, district) AS n
    FROM youbike_stations
),
placed AS (
    SELECT d.id, a.lat AS a_lat, a.lng AS a_lng, 2 * pi() * d.turn AS bearing, 250 * d.reach AS metres
    FROM draws d JOIN anchors a ON a.city = d.city AND a.district = d.district AND a.i = d.pick % a.n
)
UPDATE cafes c
SET lat = round((p.a_lat + p.metres * cos(p.bearing) / 111320)::numeric, 6),
    lng = round((p.a_lng + p.metres * sin(p.bearing) / (111320 * cos(radians(p.a_lat::float))))::numeric, 6)
FROM placed p
WHERE c.id = p.id;
SQL
        ;;
    real)
        echo "DATASET=real: export coordinates kept"
        ;;
    *)
        echo "DATASET must be demo or real, got '${DATASET}'" >&2
        false
        ;;
esac
