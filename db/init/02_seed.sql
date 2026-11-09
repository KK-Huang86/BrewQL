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

-- Community ratings, votes, views and favorites (ticket 8). Appended after searches so the
-- shared seed leaves cafes, members and searches unchanged (design D6).

-- 70% of cafes (the 140 with the lowest draw) have a Cafe Nomad row; scores in half points,
-- wifi sometimes unrated, about a third list a nearby MRT station.
INSERT INTO cafe_nomad_cache (cafe_id, cafenomad_id, name, wifi, seat, quiet, tasty, cheap, music,
                              socket, limited_time, standing_desk, mrt, synced_at)
SELECT id, 'demo-nomad-' || id, name,
       CASE WHEN r_wifi_null >= 0.1 THEN round((1 + r_wifi * 4) * 2) / 2 END,
       round((1 + r_seat * 4) * 2) / 2,
       round((1 + r_quiet * 4) * 2) / 2,
       round((1 + r_tasty * 4) * 2) / 2,
       round((1 + r_cheap * 4) * 2) / 2,
       round((1 + r_music * 4) * 2) / 2,
       (ARRAY['yes', 'maybe', 'no'])[1 + floor(r_socket * 3)::int],
       (ARRAY['no', 'maybe', 'yes'])[1 + floor(r_time * 3)::int],
       (ARRAY['no', 'maybe', 'yes'])[1 + floor(r_desk * 3)::int],
       CASE WHEN r_mrt < 0.35 THEN station END,
       now() - r_synced * interval '30 days'
FROM (
    SELECT c.id, c.name, st.station,
           random() AS r_has, random() AS r_wifi_null, random() AS r_wifi, random() AS r_seat,
           random() AS r_quiet, random() AS r_tasty, random() AS r_cheap, random() AS r_music,
           random() AS r_socket, random() AS r_time, random() AS r_desk, random() AS r_mrt,
           random() AS r_synced
    FROM cafes c
    JOIN (VALUES ('大安區', '大安站'), ('中山區', '中山站'), ('信義區', '市政府站'),
                 ('中正區', '台北車站'), ('松山區', '南京三民站'), ('內湖區', '內湖站'),
                 ('士林區', '士林站'), ('板橋區', '板橋站'), ('永和區', '頂溪站'),
                 ('新店區', '新店站')) AS st (district, station) USING (district)
    ORDER BY c.id
) drawn
ORDER BY r_has
LIMIT (SELECT round(count(*) * 0.7) FROM cafes);

-- About 900 attribute votes, mostly imported from Google, some from Cafe Nomad and members.
INSERT INTO cafe_attribute_votes (cafe_id, attribute, value, source, created_at)
SELECT c.ids[1 + floor(r_cafe * c.n)::int],
       (ARRAY['socket', 'limited_time', 'quiet', 'cheap', 'pet_friendly', 'has_pet'])[1 + floor(r_attr * 6)::int],
       CASE WHEN r_value < 0.45 THEN 'yes' WHEN r_value < 0.75 THEN 'maybe'
            WHEN r_value < 0.95 THEN 'no' ELSE 'unknown' END,
       CASE WHEN r_source < 0.72 THEN 'google' WHEN r_source < 0.85 THEN 'cafenomad' ELSE 'user' END,
       now() - r_at * interval '7 months'
FROM (
    SELECT g, random() AS r_cafe, random() AS r_attr, random() AS r_value, random() AS r_source,
           random() AS r_at
    FROM generate_series(1, 900) g
) drawn,
(SELECT array_agg(id ORDER BY id) AS ids, count(*) AS n FROM cafes) c
ORDER BY g;

-- About 185,000 views from search results or the rich menu, from the first search to now.
-- Cafes are picked by popularity: higher rating and more reviews mean more views (design D5).
-- Five 4.7+ cafes with the fewest reviews get 5% of their weight: rated highly, rarely found.
WITH members AS (
    SELECT array_agg(id ORDER BY created_at, id) AS ids,
           array_agg(created_at ORDER BY created_at, id) AS joined_at
    FROM users
),
hidden_gems AS (
    SELECT id FROM cafes WHERE rating >= 4.7 ORDER BY user_ratings_total, id LIMIT 5
),
weighted AS (
    SELECT id,
           exp((coalesce(rating, 4) - 4) * 2) * (0.5 + user_ratings_total / 1500.0)
             * CASE WHEN id IN (SELECT id FROM hidden_gems) THEN 0.05 ELSE 1 END AS w
    FROM cafes
),
-- Lower bound of each cafe's share on [0, 1); width_bucket finds the share a draw lands in.
picker AS (
    SELECT array_agg(id ORDER BY id) AS ids, array_agg(lower ORDER BY id) AS bounds
    FROM (SELECT id, (sum(w) OVER (ORDER BY id) - w) / sum(w) OVER () AS lower FROM weighted) x
),
window_start AS (
    SELECT min(created_at) AS at FROM search_logs
),
raw AS (
    SELECT g,
           ws.at + random() * (now() - ws.at) AS at,
           random() AS r_user, random() AS r_cafe, random() AS r_source
    FROM generate_series(1, 185000) g, window_start ws
)
INSERT INTO cafe_views (user_id, cafe_id, source, created_at)
SELECT m.ids[1 + floor(r.r_user * width_bucket(r.at, m.joined_at))::int],
       p.ids[width_bucket(r.r_cafe, p.bounds)],
       CASE WHEN r.r_source < 0.65 THEN 'search' ELSE 'rich_menu' END,
       r.at
FROM raw r, members m, picker p
ORDER BY r.g;

-- Favorites follow a view within two hours: about 12% of search views convert, 4% of rich
-- menu views (design D5). A member keeps only their first favorite of a cafe.
INSERT INTO favorites (user_id, cafe_id, source, created_at)
SELECT DISTINCT ON (user_id, cafe_id) user_id, cafe_id, source, fav_at
FROM (
    SELECT v.user_id, v.cafe_id, v.source, v.created_at,
           v.created_at + (0.05 + 0.95 * random()) * least(interval '2 hours', now() - v.created_at) AS fav_at,
           random() AS r_convert
    FROM cafe_views v
    ORDER BY v.id
) drawn
WHERE r_convert < CASE source WHEN 'search' THEN 0.12 ELSE 0.04 END
  AND created_at < now() - interval '1 minute'
ORDER BY user_id, cafe_id, fav_at;

-- Members come back to favorited cafes from their favorites list: 0-2 later views each.
INSERT INTO cafe_views (user_id, cafe_id, source, created_at)
SELECT user_id, cafe_id, 'favorite', created_at + r_at * (now() - created_at)
FROM (
    SELECT f.user_id, f.cafe_id, f.created_at, f.id, k, random() AS r_visit, random() AS r_at
    FROM favorites f, generate_series(1, 2) k
    ORDER BY f.id, k
) drawn
WHERE r_visit < 0.5
ORDER BY id, k;

-- Counters on cafes equal the detail rows (the real table keeps them denormalised too).
UPDATE cafes c
SET view_count = (SELECT count(*) FROM cafe_views v WHERE v.cafe_id = c.id),
    favorite_count = (SELECT count(*) FROM favorites f WHERE f.cafe_id = c.id);

ANALYZE cafes;
ANALYZE cafe_nomad_cache;
ANALYZE cafe_attribute_votes;
ANALYZE cafe_views;
ANALYZE favorites;
