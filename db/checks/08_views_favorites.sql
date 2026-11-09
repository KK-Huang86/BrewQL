-- Story (ticket 8): views and favorites mirror the Find Coffee tables, stay consistent with the
-- counters on cafes, and tell two stories: searches convert to favorites better than the LINE
-- rich menu, and some highly rated cafes are rarely favorited (design D1-D7).
DO $$
DECLARE
    missing    text;
    n_views    bigint;
    n_cafes    bigint;
    n_nomad    bigint;
    bad        bigint;
    first_day  timestamptz := (SELECT min(created_at) FROM search_logs);
    search_rate    numeric;
    menu_rate      numeric;
    median_favs    numeric;
BEGIN
    -- Tables and views exist (fails first, with a readable message, before they are built).
    SELECT string_agg(t, ', ') INTO missing
    FROM unnest(ARRAY['cafe_nomad_cache', 'cafe_attribute_votes', 'cafe_views', 'favorites',
                      'v_cafe_profile']) AS t
    WHERE to_regclass(t) IS NULL;
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'missing tables or views: %', missing;
    END IF;

    -- Votes carry no user identity (D1): same shape the real import will use.
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'cafe_attribute_votes' AND column_name = 'user_id') THEN
        RAISE EXCEPTION 'cafe_attribute_votes must not have user_id';
    END IF;

    -- Scale: about 200,000 views; about 70% of cafes have community ratings.
    EXECUTE 'SELECT count(*) FROM cafe_views' INTO n_views;
    IF n_views NOT BETWEEN 180000 AND 220000 THEN
        RAISE EXCEPTION 'cafe_views has % rows, expected about 200,000', n_views;
    END IF;
    n_cafes := (SELECT count(*) FROM cafes);
    EXECUTE 'SELECT count(DISTINCT cafe_id) FROM cafe_nomad_cache' INTO n_nomad;
    IF n_nomad::numeric / n_cafes NOT BETWEEN 0.6 AND 0.8 THEN
        RAISE EXCEPTION '% of % cafes have community ratings, expected about 70%%', n_nomad, n_cafes;
    END IF;

    -- Counters on cafes match the detail rows, cafe by cafe.
    EXECUTE $q$
        SELECT count(*) FROM cafes c
        WHERE c.favorite_count <> (SELECT count(*) FROM favorites f WHERE f.cafe_id = c.id)
           OR c.view_count <> (SELECT count(*) FROM cafe_views v WHERE v.cafe_id = c.id)
    $q$ INTO bad;
    IF bad > 0 THEN
        RAISE EXCEPTION '% cafes have favorite_count or view_count out of step with the detail rows', bad;
    END IF;

    -- One favorite per member and cafe.
    EXECUTE $q$
        SELECT count(*) FROM (SELECT 1 FROM favorites GROUP BY user_id, cafe_id HAVING count(*) > 1) d
    $q$ INTO bad;
    IF bad > 0 THEN
        RAISE EXCEPTION '% member-cafe pairs are favorited more than once', bad;
    END IF;

    -- Favorites come from search or the rich menu, each after a matching earlier view (D2).
    EXECUTE $q$
        SELECT count(*) FROM favorites f
        WHERE f.source NOT IN ('search', 'rich_menu')
           OR NOT EXISTS (SELECT 1 FROM cafe_views v
                          WHERE v.user_id = f.user_id AND v.cafe_id = f.cafe_id
                            AND v.source = f.source AND v.created_at < f.created_at)
    $q$ INTO bad;
    IF bad > 0 THEN
        RAISE EXCEPTION '% favorites have an unexpected source or no earlier matching view', bad;
    END IF;

    -- Views and favorites happen after the member joined, inside the search window, not in the future.
    EXECUTE $q$
        SELECT (SELECT count(*) FROM cafe_views v JOIN users u ON u.id = v.user_id
                WHERE v.created_at < u.created_at OR v.created_at < $1 OR v.created_at > now())
             + (SELECT count(*) FROM favorites f JOIN users u ON u.id = f.user_id
                WHERE f.created_at < u.created_at OR f.created_at < $1 OR f.created_at > now())
    $q$ INTO bad USING first_day;
    IF bad > 0 THEN
        RAISE EXCEPTION '% views or favorites fall before signup or outside the search window', bad;
    END IF;

    -- v_cafe_profile keeps every cafe; cafes without community ratings show NULL (D7).
    EXECUTE $q$
        SELECT (SELECT count(*) FROM cafes) - (SELECT count(*) FROM v_cafe_profile)
             + (SELECT count(*) FROM v_cafe_profile p
                WHERE p.wifi IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM cafe_nomad_cache n WHERE n.cafe_id = p.id))
    $q$ INTO bad;
    IF bad <> 0 THEN
        RAISE EXCEPTION 'v_cafe_profile does not list every cafe once with NULL ratings where missing';
    END IF;

    -- v_daily_activity adds daily views and new favorites that sum to the detail rows (D7).
    EXECUTE $q$
        SELECT (SELECT count(*) FROM cafe_views) - sum(views)
             + (SELECT count(*) FROM favorites) - sum(new_favorites)
             + count(*) FILTER (WHERE views IS NULL OR new_favorites IS NULL)
        FROM v_daily_activity
    $q$ INTO bad;
    IF bad IS DISTINCT FROM 0 THEN
        RAISE EXCEPTION 'v_daily_activity views or new_favorites do not sum to the detail rows';
    END IF;

    -- Story 1: favorite conversion = favorites from an entry point / views from it (D3).
    EXECUTE $q$
        SELECT (SELECT count(*) FROM favorites WHERE source = 'search')::numeric
                 / nullif((SELECT count(*) FROM cafe_views WHERE source = 'search'), 0),
               (SELECT count(*) FROM favorites WHERE source = 'rich_menu')::numeric
                 / nullif((SELECT count(*) FROM cafe_views WHERE source = 'rich_menu'), 0)
    $q$ INTO search_rate, menu_rate;
    IF search_rate IS NULL OR menu_rate IS NULL OR search_rate <= menu_rate THEN
        RAISE EXCEPTION 'conversion: search % vs rich_menu %, expected search higher', search_rate, menu_rate;
    END IF;

    -- Story 2: at least one cafe rated 4.7+ has fewer favorites than the median cafe (D5).
    EXECUTE 'SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY favorite_count) FROM cafes'
        INTO median_favs;
    EXECUTE 'SELECT count(*) FROM cafes WHERE rating >= 4.7 AND favorite_count < $1'
        INTO bad USING median_favs;
    IF bad = 0 THEN
        RAISE EXCEPTION 'no cafe rated 4.7+ has fewer favorites than the median (%)', median_favs;
    END IF;
END $$;
