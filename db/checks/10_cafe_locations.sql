-- Cafe coordinates (cafe-transit-distance D6): after init every cafe has coordinates inside
-- Taipei and New Taipei, so v_cafe_transit drops nobody and no distance is measured from a
-- typo. Demo cafes are generated next to a YouBike station in their own district, so a demo
-- cafe more than 5 km from every MRT station means the generator broke.
DO $$
DECLARE
    bad text;
BEGIN
    SELECT string_agg(place_id, ', ' ORDER BY place_id) INTO bad
    FROM cafes WHERE lat IS NULL OR lng IS NULL;
    IF bad IS NOT NULL THEN
        RAISE EXCEPTION 'cafes without coordinates: %', bad;
    END IF;

    SELECT string_agg(place_id || ' (' || lat || ', ' || lng || ')', ', ' ORDER BY place_id) INTO bad
    FROM cafes WHERE lat NOT BETWEEN 24.6 AND 25.4 OR lng NOT BETWEEN 121.2 AND 122.1;
    IF bad IS NOT NULL THEN
        RAISE EXCEPTION 'cafes outside Taipei and New Taipei: %', bad;
    END IF;

    SELECT string_agg(c.place_id || ' ' || t.mrt_distance_m || ' m', ', ' ORDER BY c.place_id) INTO bad
    FROM cafes c JOIN v_cafe_transit t ON t.cafe_id = c.id
    WHERE c.place_id LIKE 'demo-%' AND t.mrt_distance_m > 5000;
    IF bad IS NOT NULL THEN
        RAISE EXCEPTION 'demo cafes far from every MRT station: %', bad;
    END IF;
END $$;
