-- Story: 2,000 demo members and about 50,000 searches.
DO $$
DECLARE
    n_users  bigint := (SELECT count(*) FROM users);
    n_search bigint := (SELECT count(*) FROM search_logs);
BEGIN
    IF n_users <> 2000 THEN
        RAISE EXCEPTION 'users: expected 2000 rows, got %', n_users;
    END IF;
    IF n_search NOT BETWEEN 45000 AND 55000 THEN
        RAISE EXCEPTION 'search_logs: expected about 50000 rows, got %', n_search;
    END IF;
END $$;
