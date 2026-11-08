-- Story: a member searches only after joining, so joins of users and search_logs read sensibly.
DO $$
DECLARE
    early bigint;
BEGIN
    SELECT count(*) INTO early
    FROM search_logs s JOIN users u ON u.id = s.user_id
    WHERE s.created_at < u.created_at;
    IF early > 0 THEN
        RAISE EXCEPTION '% searches happen before their member joined', early;
    END IF;
END $$;
