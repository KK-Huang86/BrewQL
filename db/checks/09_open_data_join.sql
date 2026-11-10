-- Open data joins by name (import-open-data D5): every district that cafes, searches,
-- universities, YouBike and MRT stations (import-transit-open-data D4) use has a population row,
-- so a spelling mismatch (臺/台, a renamed district) fails here instead of silently dropping rows from a per-capita answer. Real-mode cafes with an
-- unknown location (NULL city) are skipped: they join nothing by design.
DO $$
DECLARE
    missing text;
BEGIN
    SELECT string_agg(DISTINCT src || ':' || city || district, ', ') INTO missing
    FROM (
        SELECT 'cafes' AS src, city, district FROM cafes
        UNION ALL SELECT 'search_logs', city, district FROM search_logs
        UNION ALL SELECT 'universities', city, district FROM universities
        UNION ALL SELECT 'youbike_stations', city, district FROM youbike_stations
        UNION ALL SELECT 'mrt_stations', city, district FROM mrt_stations
    ) used
    WHERE NOT EXISTS (
        SELECT 1 FROM district_population p WHERE p.city = used.city AND p.district = used.district
    );
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'districts without population data: %', missing;
    END IF;
END $$;
