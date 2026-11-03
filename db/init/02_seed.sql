-- Deterministic demo cafes (no real Find Coffee data). setseed fixes random(),
-- so recreating the volume yields the same per-district counts and values.
SELECT setseed(0.42);

-- 200 cafes over 10 districts; 內湖區 is deliberately sparse (used by later tickets).
CREATE TEMP TABLE districts (city TEXT, district TEXT, cafe_n INT);
INSERT INTO districts VALUES
    ('台北市', '大安區', 40), ('台北市', '中山區', 35), ('台北市', '信義區', 25),
    ('台北市', '中正區', 25), ('台北市', '松山區', 20), ('台北市', '內湖區', 3),
    ('台北市', '士林區', 12), ('新北市', '板橋區', 18), ('新北市', '永和區', 12),
    ('新北市', '新店區', 10);

INSERT INTO cafes (place_id, name, address, city, district, rating, user_ratings_total,
                   limited_time, has_socket, pet_friendly, has_pet, created_at)
SELECT
    'demo-' || d.district || '-' || g,
    d.district || '示範咖啡 ' || g,
    d.city || d.district || '示範路 ' || g || ' 號',
    d.city, d.district,
    round((3.4 + random() * 1.6)::numeric, 1),
    (random() * 1500)::int,
    (ARRAY['no', 'maybe', 'yes'])[1 + floor(random() * 3)::int],
    (ARRAY['yes', 'maybe', 'no'])[1 + floor(random() * 3)::int],
    random() < 0.3,
    random() < 0.1,
    TIMESTAMPTZ '2026-01-01' - (random() * 700 || ' days')::interval
FROM districts d, generate_series(1, d.cafe_n) g
ORDER BY d.city, d.district, g;

ANALYZE cafes;
