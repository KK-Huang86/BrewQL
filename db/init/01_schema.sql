-- Mirrors the Find Coffee `cafes` table, plus simulated members and searches (no real user data).
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
    pet_friendly       BOOLEAN NOT NULL DEFAULT FALSE,
    has_pet            BOOLEAN NOT NULL DEFAULT FALSE,
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
)
SELECT d.day,
       coalesce(s.n, 0) AS searches,
       coalesce(u.n, 0) AS new_users
FROM days d
LEFT JOIN searches s USING (day)
LEFT JOIN signups u USING (day);
