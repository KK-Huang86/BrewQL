-- Story: 內湖區 is searched a lot (top 3 by volume) but most often finds nothing (highest
-- zero-result rate = searches with result_count = 0 / searches in the district; design D2).
DO $$
DECLARE
    volume_rank int;
    gap_leader  text;
BEGIN
    SELECT rank INTO volume_rank FROM (
        SELECT district, rank() OVER (ORDER BY count(*) DESC) AS rank
        FROM search_logs GROUP BY district
    ) r WHERE district = '內湖區';
    IF volume_rank IS NULL OR volume_rank > 3 THEN
        RAISE EXCEPTION '內湖區 search volume rank is %, expected top 3', volume_rank;
    END IF;

    SELECT district INTO gap_leader
    FROM search_logs
    GROUP BY district
    ORDER BY count(*) FILTER (WHERE result_count = 0)::numeric / count(*) DESC
    LIMIT 1;
    IF gap_leader IS DISTINCT FROM '內湖區' THEN
        RAISE EXCEPTION 'highest zero-result rate is %, expected 內湖區', gap_leader;
    END IF;
END $$;
