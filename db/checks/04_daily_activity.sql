-- Story: v_daily_activity has one row per day from the first search to today, zeros included.
DO $$
DECLARE
    first_day date := (SELECT min(created_at)::date FROM search_logs);
    days      bigint;
    distinct_days bigint;
    gaps      bigint;
    nulls     bigint;
    total_searches bigint;
BEGIN
    SELECT count(*), count(DISTINCT day), count(*) FILTER (WHERE searches IS NULL OR new_users IS NULL),
           sum(searches)
    INTO days, distinct_days, nulls, total_searches
    FROM v_daily_activity;
    gaps := (current_date - first_day + 1) - distinct_days;
    IF days <> distinct_days OR gaps <> 0 THEN
        RAISE EXCEPTION 'v_daily_activity: % rows, % distinct days, % missing days since %', days, distinct_days, gaps, first_day;
    END IF;
    IF nulls > 0 THEN
        RAISE EXCEPTION 'v_daily_activity: % rows with NULL instead of 0', nulls;
    END IF;
    IF total_searches <> (SELECT count(*) FROM search_logs) THEN
        RAISE EXCEPTION 'v_daily_activity: daily searches sum to %, search_logs has %', total_searches,
            (SELECT count(*) FROM search_logs);
    END IF;
END $$;
