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

-- Members and searches. Appended after cafes so the shared seed leaves cafes unchanged.
-- Dates count back from the day the database is built (design D1): "最近半年" always has data,
-- and a rebuild gives the same shape shifted to the new build day.

-- 2,000 members who joined over the last two years.
INSERT INTO users (member_type, status, created_at)
SELECT
    CASE WHEN random() < 0.15 THEN 'premium' ELSE 'free' END,
    CASE WHEN random() < 0.85 THEN 'active' ELSE 'inactive' END,
    now() - random() * interval '730 days'
FROM generate_series(1, 2000);

-- About 50,000 searches over the last six calendar months. Exam season (May, Jun, Nov, Dec)
-- makes "no time limit + sockets" searches far more likely (design D2). Each search belongs to
-- a member who had already joined when it happened.
WITH members AS (
    SELECT array_agg(id ORDER BY created_at, id) AS ids FROM users
),
-- Search share per district (design D1): 內湖區 is searched a lot but has only 3 cafes,
-- so its searches often find nothing. The shares sum to 1; cum is the running total.
places AS (
    SELECT array_agg(city ORDER BY city, district) AS cities,
           array_agg(district ORDER BY city, district) AS districts,
           array_agg(cafe_n ORDER BY city, district) AS supply,
           array_agg(cum ORDER BY city, district) AS cum
    FROM (
        SELECT d.*, sum(w.share) OVER (ORDER BY d.city, d.district) AS cum
        FROM districts d
        JOIN (VALUES ('大安區', 0.18), ('內湖區', 0.16), ('中山區', 0.14), ('信義區', 0.12),
                     ('中正區', 0.10), ('松山區', 0.08), ('板橋區', 0.07), ('士林區', 0.06),
                     ('永和區', 0.05), ('新店區', 0.04)) AS w (district, share) USING (district)
    ) weighted
),
raw AS (
    SELECT g,
           -- A share of the exact span back to the same date six months ago (not a fixed 182 days).
           now() - random() * (now() - (now() - interval '6 months')) AS at,
           random() AS r_user,
           random() AS r_place,
           random() AS r_work, random() AS r_time, random() AS r_socket, random() AS r_pet,
           random() AS r_query, random() AS r_result
    FROM generate_series(1, 50000) g
),
shaped AS (
    SELECT raw.*,
           -- First district whose running share passes the draw: a weighted pick.
           (SELECT min(i) FROM unnest(p.cum) WITH ORDINALITY AS c (total, i) WHERE c.total > raw.r_place) AS place,
           -- Members who joined by then, oldest first; pick one of them.
           (SELECT count(*) FROM users u WHERE u.created_at <= raw.at) AS joined,
           r_work < CASE WHEN extract(month FROM at) IN (5, 6, 11, 12) THEN 0.35 ELSE 0.12 END AS work_friendly
    FROM raw, places p
)
INSERT INTO search_logs (user_id, query_text, city, district, filters, result_count, created_at)
SELECT
    m.ids[1 + floor(s.r_user * s.joined)::int],
    p.districts[s.place] || (ARRAY['咖啡廳', '讀書咖啡', '安靜咖啡', '不限時咖啡', '寵物友善咖啡'])[1 + floor(s.r_query * 5)::int],
    p.cities[s.place],
    p.districts[s.place],
    jsonb_strip_nulls(jsonb_build_object(
        'no_time_limit', CASE WHEN s.work_friendly OR s.r_time < 0.15 THEN true END,
        'has_socket',    CASE WHEN s.work_friendly OR s.r_socket < 0.15 THEN true END,
        'pet_friendly',  CASE WHEN s.r_pet < 0.10 THEN true END
    )),
    -- Fewer cafes in a district means fewer results, hence 內湖區's high zero-result rate.
    floor(p.supply[s.place] * s.r_result * 0.6)::int,
    s.at
FROM shaped s, places p, members m
ORDER BY s.g;

ANALYZE users;
ANALYZE search_logs;
