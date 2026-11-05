-- Mirrors the Find Coffee `cafes` table. Behaviour tables arrive in later tickets.
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
