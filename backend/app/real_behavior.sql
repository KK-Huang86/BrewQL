-- Simulated members and behaviour for real cafes (import-real-cafes D9). Runs inside the import
-- transaction, after the real cafes, votes and Cafe Nomad rows are written. Follows the demo seed
-- (db/init/02_seed.sql) without its stories: each district is searched in proportion to its cafes.
-- No real member, search, view, favorite or member vote ever reaches this database.
SELECT setseed(0.42);

-- 2,000 members who joined over the last two years.
INSERT INTO users (member_type, status, created_at)
SELECT
    CASE WHEN random() < 0.15 THEN 'premium' ELSE 'free' END,
    CASE WHEN random() < 0.85 THEN 'active' ELSE 'inactive' END,
    now() - random() * interval '730 days'
FROM generate_series(1, 2000);

-- About 50,000 searches over the last six calendar months, exam season as in demo. Only districts
-- with real cafes are searched; cum is the running share, weighted by each district's cafe count.
WITH members AS (
    SELECT array_agg(id ORDER BY created_at, id) AS ids,
           array_agg(created_at ORDER BY created_at, id) AS joined_at
    FROM users
),
places AS (
    SELECT array_agg(city ORDER BY city, district) AS cities,
           array_agg(district ORDER BY city, district) AS districts,
           array_agg(cafe_n ORDER BY city, district) AS supply,
           array_agg(cum ORDER BY city, district) AS cum
    FROM (
        SELECT city, district, cafe_n,
               sum(cafe_n) OVER (ORDER BY city, district)::float / sum(cafe_n) OVER () AS cum
        FROM (SELECT city, district, count(*) AS cafe_n FROM cafes
              WHERE district IS NOT NULL GROUP BY city, district) d
    ) weighted
),
raw AS (
    SELECT g,
           now() - random() * (now() - (now() - interval '6 months')) AS at,
           random() AS r_user,
           random() AS r_place,
           random() AS r_work, random() AS r_time, random() AS r_socket, random() AS r_pet,
           random() AS r_query, random() AS r_result
    FROM generate_series(1, 50000) g
),
shaped AS (
    SELECT raw.*,
           (SELECT min(i) FROM unnest(p.cum) WITH ORDINALITY AS c (total, i) WHERE c.total > raw.r_place) AS place,
           -- Members who joined by then: width_bucket counts the sorted join times at or before it.
           width_bucket(raw.at, m.joined_at) AS joined,
           r_work < CASE WHEN extract(month FROM at) IN (5, 6, 11, 12) THEN 0.35 ELSE 0.12 END AS work_friendly
    FROM raw, places p, members m
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
    floor(p.supply[s.place] * s.r_result * 0.6)::int,
    s.at
FROM shaped s, places p, members m
-- A draw of exactly the last share's total would find no district; such searches are dropped.
WHERE s.place IS NOT NULL AND s.joined > 0
ORDER BY s.g;

-- About 185,000 views, picked by popularity: higher rating and more reviews mean more views.
WITH members AS (
    SELECT array_agg(id ORDER BY created_at, id) AS ids,
           array_agg(created_at ORDER BY created_at, id) AS joined_at
    FROM users
),
weighted AS (
    SELECT id, exp((coalesce(rating, 4) - 4) * 2) * (0.5 + user_ratings_total / 1500.0) AS w
    FROM cafes
),
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
WHERE width_bucket(r.at, m.joined_at) > 0
ORDER BY r.g;

-- Favorites follow a view within two hours: about 12% of search views, 4% of rich menu views.
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

-- Counters on cafes equal the detail rows, as in demo.
UPDATE cafes c
SET view_count = (SELECT count(*) FROM cafe_views v WHERE v.cafe_id = c.id),
    favorite_count = (SELECT count(*) FROM favorites f WHERE f.cafe_id = c.id);
