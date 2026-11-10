-- Mirrors the Find Coffee tables, plus simulated members, searches, views and favorites (no real user data).
CREATE TABLE cafes (
    id                 BIGSERIAL PRIMARY KEY,
    place_id           TEXT UNIQUE,
    name               TEXT NOT NULL,
    address            TEXT NOT NULL,
    city               TEXT,              -- parsed from address on import
    district           TEXT,              -- parsed from address on import
    rating             NUMERIC(2, 1),
    user_ratings_total INTEGER NOT NULL DEFAULT 0,
    limited_time       TEXT CHECK (limited_time IN ('yes', 'maybe', 'no')),
    has_socket         TEXT CHECK (has_socket IN ('yes', 'maybe', 'no')),
    pet_friendly       BOOLEAN DEFAULT FALSE,   -- NULL: unknown (real cafes, import-real-cafes D8)
    has_pet            BOOLEAN DEFAULT FALSE,
    favorite_count     INTEGER NOT NULL DEFAULT 0,   -- kept equal to rows in favorites
    view_count         INTEGER NOT NULL DEFAULT 0,   -- kept equal to rows in cafe_views
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Simulated members. Deliberately no LINE ID, name, email or any field that identifies a person.
CREATE TABLE users (
    id          BIGSERIAL PRIMARY KEY,
    member_type TEXT NOT NULL CHECK (member_type IN ('free', 'premium')),
    status      TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
    created_at  TIMESTAMPTZ NOT NULL
);

-- One row per search. filters holds only the options the user ticked, as booleans:
-- no_time_limit (不限時), has_socket (有插座), pet_friendly (寵物友善).
CREATE TABLE search_logs (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users (id),
    query_text   TEXT NOT NULL,
    city         TEXT NOT NULL,
    district     TEXT NOT NULL,
    filters      JSONB NOT NULL DEFAULT '{}',
    result_count INTEGER NOT NULL CHECK (result_count >= 0),
    created_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX search_logs_created_at ON search_logs (created_at);

-- Cafe Nomad community ratings, columns taken from the Find Coffee export (design D1).
-- The real table has no cafe_id and is matched by name and location; here cafe_id stands for
-- an already matched row, so about 70% of cafes have one.
CREATE TABLE cafe_nomad_cache (
    id            BIGSERIAL PRIMARY KEY,
    cafe_id       BIGINT NOT NULL UNIQUE REFERENCES cafes (id),
    cafenomad_id  TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    wifi          NUMERIC(2, 1) CHECK (wifi BETWEEN 0 AND 5),
    seat          NUMERIC(2, 1) CHECK (seat BETWEEN 0 AND 5),
    quiet         NUMERIC(2, 1) CHECK (quiet BETWEEN 0 AND 5),
    tasty         NUMERIC(2, 1) CHECK (tasty BETWEEN 0 AND 5),
    cheap         NUMERIC(2, 1) CHECK (cheap BETWEEN 0 AND 5),
    music         NUMERIC(2, 1) CHECK (music BETWEEN 0 AND 5),
    socket        TEXT CHECK (socket IN ('yes', 'maybe', 'no')),
    limited_time  TEXT CHECK (limited_time IN ('yes', 'maybe', 'no')),
    standing_desk TEXT CHECK (standing_desk IN ('yes', 'maybe', 'no')),
    mrt           TEXT,
    synced_at     TIMESTAMPTZ NOT NULL
);

-- Attribute votes behind cafes.has_socket and friends. No user_id: the real export carries
-- real member ids on user votes, and the import keeps only the vote itself (design D1).
CREATE TABLE cafe_attribute_votes (
    id         BIGSERIAL PRIMARY KEY,
    cafe_id    BIGINT NOT NULL REFERENCES cafes (id),
    attribute  TEXT NOT NULL CHECK (attribute IN ('socket', 'limited_time', 'quiet', 'cheap',
                                                  'pet_friendly', 'has_pet')),
    value      TEXT NOT NULL CHECK (value IN ('yes', 'maybe', 'no', 'unknown')),
    source     TEXT NOT NULL CHECK (source IN ('google', 'cafenomad', 'user')),
    created_at TIMESTAMPTZ NOT NULL
);

-- One row per cafe page view, by entry point: search results, the favorites list or the
-- LINE rich menu (design D2).
CREATE TABLE cafe_views (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id),
    cafe_id    BIGINT NOT NULL REFERENCES cafes (id),
    source     TEXT NOT NULL CHECK (source IN ('search', 'favorite', 'rich_menu')),
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX cafe_views_created_at ON cafe_views (created_at);
CREATE INDEX cafe_views_cafe_id ON cafe_views (cafe_id);

-- A member favorites a cafe at most once; source is the entry point they favorited it from.
CREATE TABLE favorites (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id),
    cafe_id    BIGINT NOT NULL REFERENCES cafes (id),
    source     TEXT NOT NULL CHECK (source IN ('search', 'rich_menu')),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (user_id, cafe_id)
);
CREATE INDEX favorites_cafe_id ON favorites (cafe_id);

-- Every cafe with its community ratings; NULL where Cafe Nomad has no row (design D7).
CREATE VIEW v_cafe_profile AS
SELECT c.*, n.wifi, n.seat, n.quiet, n.tasty, n.cheap, n.music, n.mrt
FROM cafes c
LEFT JOIN cafe_nomad_cache n ON n.cafe_id = c.id;

-- One row per day from the first search to today; days without activity are 0, not missing.
CREATE VIEW v_daily_activity AS
WITH days AS (
    SELECT generate_series((SELECT min(created_at)::date FROM search_logs), current_date, interval '1 day')::date AS day
),
searches AS (
    SELECT created_at::date AS day, count(*) AS n FROM search_logs GROUP BY 1
),
signups AS (
    SELECT created_at::date AS day, count(*) AS n FROM users GROUP BY 1
),
views AS (
    SELECT created_at::date AS day, count(*) AS n FROM cafe_views GROUP BY 1
),
favs AS (
    SELECT created_at::date AS day, count(*) AS n FROM favorites GROUP BY 1
)
SELECT d.day,
       coalesce(s.n, 0) AS searches,
       coalesce(u.n, 0) AS new_users,
       coalesce(v.n, 0) AS views,
       coalesce(f.n, 0) AS new_favorites
FROM days d
LEFT JOIN searches s USING (day)
LEFT JOIN signups u USING (day)
LEFT JOIN views v USING (day)
LEFT JOIN favs f USING (day);

-- Government open data (import-open-data): fixed snapshots for Taipei and New Taipei, loaded by
-- 06_open_data.sh from db/init/open_data. city and district use the demo spelling, so they join
-- cafes and search_logs directly.
CREATE TABLE district_population (
    city       TEXT NOT NULL,
    district   TEXT NOT NULL,
    population INTEGER NOT NULL CHECK (population > 0),
    area_km2   NUMERIC(8, 4) NOT NULL CHECK (area_km2 > 0),
    as_of      DATE NOT NULL,                     -- population at the end of this day
    PRIMARY KEY (city, district)
);

CREATE TABLE universities (
    code      TEXT PRIMARY KEY,                   -- MOE school code
    name      TEXT NOT NULL,
    ownership TEXT NOT NULL CHECK (ownership IN ('公立', '私立')),
    level     TEXT NOT NULL,                      -- MOE 體制, e.g. 一般大學, 技專校院
    city      TEXT NOT NULL,
    district  TEXT NOT NULL
);

-- Transit open data (import-transit-open-data): stations in service on the download day (as_of).
-- Joined to the rest by district; lat/lng are kept for the distance view of cafe-transit-distance.
CREATE TABLE youbike_stations (
    station_no TEXT PRIMARY KEY,                  -- official sno
    name       TEXT NOT NULL,                     -- without the YouBike2.0_ prefix
    city       TEXT NOT NULL,
    district   TEXT NOT NULL,                     -- 臺大公館校區 stations count as 大安區
    docks      INTEGER NOT NULL CHECK (docks >= 0),
    lat        NUMERIC(9, 6) NOT NULL,
    lng        NUMERIC(9, 6) NOT NULL,
    as_of      DATE NOT NULL                      -- download day of the live feed
);

-- Taipei Metro (TRTC) stations built from their exits; no Airport MRT or light rail.
CREATE TABLE mrt_stations (
    name       TEXT PRIMARY KEY,                  -- e.g. 板橋, 台北車站
    city       TEXT NOT NULL,
    district   TEXT NOT NULL,
    exit_count INTEGER NOT NULL CHECK (exit_count > 0),
    lat        NUMERIC(9, 6) NOT NULL,            -- average of the exits
    lng        NUMERIC(9, 6) NOT NULL,
    as_of      DATE NOT NULL                      -- download day of the exit file
);
