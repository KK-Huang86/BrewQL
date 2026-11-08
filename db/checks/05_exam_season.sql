-- Story: in exam months (May, Jun, Nov, Dec) more searches ask for no time limit plus sockets.
DO $$
DECLARE
    exam_ratio  numeric;
    other_ratio numeric;
BEGIN
    WITH monthly AS (
        SELECT extract(month FROM created_at) IN (5, 6, 11, 12) AS exam,
               avg((filters @> '{"no_time_limit": true, "has_socket": true}')::int) AS ratio
        FROM search_logs
        GROUP BY date_trunc('month', created_at), exam
    )
    SELECT avg(ratio) FILTER (WHERE exam), avg(ratio) FILTER (WHERE NOT exam)
    INTO exam_ratio, other_ratio
    FROM monthly;
    IF exam_ratio IS NULL OR other_ratio IS NULL THEN
        RAISE EXCEPTION 'need both exam and other months, got exam=% other=%', exam_ratio, other_ratio;
    END IF;
    IF exam_ratio <= other_ratio THEN
        RAISE EXCEPTION 'exam months ratio % is not above other months %', round(exam_ratio, 3), round(other_ratio, 3);
    END IF;
END $$;
