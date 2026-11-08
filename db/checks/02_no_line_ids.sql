-- Story: demo members carry no LINE or other real-person identifiers.
DO $$
DECLARE
    leaked text;
BEGIN
    -- The tables must exist, or "no matching column" would pass vacuously.
    IF to_regclass('public.users') IS NULL OR to_regclass('public.search_logs') IS NULL THEN
        RAISE EXCEPTION 'users and search_logs must exist';
    END IF;
    SELECT string_agg(table_name || '.' || column_name, ', ') INTO leaked
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name IN ('users', 'search_logs')
      AND column_name ~* '(line|display_name|email|phone|picture)';
    IF leaked IS NOT NULL THEN
        RAISE EXCEPTION 'identifying columns found: %', leaked;
    END IF;
END $$;
