-- Story: searches cover the six months up to the day the database was built (design D1).
DO $$
DECLARE
    first_at timestamptz;
    last_at  timestamptz;
BEGIN
    SELECT min(created_at), max(created_at) INTO first_at, last_at FROM search_logs;
    IF last_at IS NULL THEN
        RAISE EXCEPTION 'search_logs is empty';
    END IF;
    IF last_at > now() THEN
        RAISE EXCEPTION 'searches in the future: latest is %', last_at;
    END IF;
    -- Checked relative to the latest row so the check still holds days after the build.
    -- Spec: no earlier than six months before the build (182 days would overshoot e.g. Sep-Mar).
    IF first_at < last_at - interval '6 months' THEN
        RAISE EXCEPTION 'searches span more than six months: % to %', first_at, last_at;
    END IF;
    IF first_at > last_at - interval '5 months' THEN
        RAISE EXCEPTION 'searches span less than five months: % to %', first_at, last_at;
    END IF;
END $$;
