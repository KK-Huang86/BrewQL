-- Story (ticket 8): views and favorites mirror the Find Coffee tables, stay consistent with the
-- counters on cafes, and tell two stories: searches convert to favorites better than the LINE
-- rich menu, and some highly rated cafes are rarely favorited (design D1-D7).
DO $$
DECLARE
    missing      text;
    n_views      bigint;
    n_cafes      bigint;
    n_nomad      bigint;
    off_counters bigint;
    duplicates   bigint;
    orphan_favs  bigint;
    out_of_range bigint;
    profile_gaps bigint;
    daily_gaps   bigint;
    hidden_gems  bigint;
    first_day    timestamptz := (SELECT min(created_at) FROM search_logs);
    search_rate  numeric;
    menu_rate    numeric;
    median_favs  numeric;
BEGIN
    -- Tables and views exist. Checked first so a missing one fails with a readable message;
    -- PL/pgSQL plans each statement only when it reaches it.
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
    n_views := (SELECT count(*) FROM cafe_views);
    IF n_views NOT BETWEEN 180000 AND 220000 THEN
        RAISE EXCEPTION 'cafe_views has % rows, expected about 200,000', n_views;
    END IF;
    n_cafes := (SELECT count(*) FROM cafes);
    n_nomad := (SELECT count(DISTINCT cafe_id) FROM cafe_nomad_cache);
    IF n_nomad::numeric / n_cafes NOT BETWEEN 0.6 AND 0.8 THEN
        RAISE EXCEPTION '% of % cafes have community ratings, expected about 70%%', n_nomad, n_cafes;
    END IF;

    -- Counters on cafes match the detail rows, cafe by cafe.
    SELECT count(*) INTO off_counters FROM cafes c
    WHERE c.favorite_count <> (SELECT count(*) FROM favorites f WHERE f.cafe_id = c.id)
       OR c.view_count <> (SELECT count(*) FROM cafe_views v WHERE v.cafe_id = c.id);
    IF off_counters > 0 THEN
        RAISE EXCEPTION '% cafes have favorite_count or view_count out of step with the detail rows', off_counters;
    END IF;

    -- One favorite per member and cafe.
    SELECT count(*) INTO duplicates
    FROM (SELECT 1 FROM favorites GROUP BY user_id, cafe_id HAVING count(*) > 1) d;
    IF duplicates > 0 THEN
        RAISE EXCEPTION '% member-cafe pairs are favorited more than once', duplicates;
    END IF;

    -- Favorites come from search or the rich menu, each after a matching earlier view (D2).
    SELECT count(*) INTO orphan_favs FROM favorites f
    WHERE f.source NOT IN ('search', 'rich_menu')
       OR NOT EXISTS (SELECT 1 FROM cafe_views v
                      WHERE v.user_id = f.user_id AND v.cafe_id = f.cafe_id
                        AND v.source = f.source AND v.created_at < f.created_at);
    IF orphan_favs > 0 THEN
        RAISE EXCEPTION '% favorites have an unexpected source or no earlier matching view', orphan_favs;
    END IF;

    -- Views and favorites happen after the member joined, inside the search window (which
    -- check 03 bounds to the six months before the build), not in the future.
    out_of_range :=
        (SELECT count(*) FROM cafe_views v JOIN users u ON u.id = v.user_id
         WHERE v.created_at < u.created_at OR v.created_at < first_day OR v.created_at > now())
      + (SELECT count(*) FROM favorites f JOIN users u ON u.id = f.user_id
         WHERE f.created_at < u.created_at OR f.created_at < first_day OR f.created_at > now());
    IF out_of_range > 0 THEN
        RAISE EXCEPTION '% views or favorites fall before signup or outside the search window', out_of_range;
    END IF;

    -- v_cafe_profile keeps every cafe once; cafes without community ratings show NULL (D7).
    profile_gaps :=
        (SELECT count(*) FROM cafes) - (SELECT count(*) FROM v_cafe_profile)
      + (SELECT count(*) FROM v_cafe_profile p
         WHERE p.wifi IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM cafe_nomad_cache n WHERE n.cafe_id = p.id));
    IF profile_gaps <> 0 THEN
        RAISE EXCEPTION 'v_cafe_profile does not list every cafe once with NULL ratings where missing';
    END IF;

    -- v_daily_activity adds daily views and new favorites that sum to the detail rows (D7).
    SELECT (SELECT count(*) FROM cafe_views) - sum(views)
         + (SELECT count(*) FROM favorites) - sum(new_favorites)
         + count(*) FILTER (WHERE views IS NULL OR new_favorites IS NULL)
    INTO daily_gaps
    FROM v_daily_activity;
    IF daily_gaps IS DISTINCT FROM 0 THEN
        RAISE EXCEPTION 'v_daily_activity views or new_favorites do not sum to the detail rows';
    END IF;

    -- Story 1: favorite conversion = favorites from an entry point / views from it (D3).
    search_rate := (SELECT count(*) FROM favorites WHERE source = 'search')::numeric
                   / nullif((SELECT count(*) FROM cafe_views WHERE source = 'search'), 0);
    menu_rate := (SELECT count(*) FROM favorites WHERE source = 'rich_menu')::numeric
                 / nullif((SELECT count(*) FROM cafe_views WHERE source = 'rich_menu'), 0);
    IF search_rate IS NULL OR menu_rate IS NULL OR search_rate <= menu_rate THEN
        RAISE EXCEPTION 'conversion: search % vs rich_menu %, expected search higher', search_rate, menu_rate;
    END IF;

    -- Story 2: at least one cafe rated 4.7+ has fewer favorites than the median cafe (D5).
    median_favs := (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY favorite_count) FROM cafes);
    hidden_gems := (SELECT count(*) FROM cafes WHERE rating >= 4.7 AND favorite_count < median_favs);
    IF hidden_gems = 0 THEN
        RAISE EXCEPTION 'no cafe rated 4.7+ has fewer favorites than the median (%)', median_favs;
    END IF;
END $$;
