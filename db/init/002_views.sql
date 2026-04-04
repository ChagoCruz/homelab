CREATE OR REPLACE VIEW vw_daily_diet_summary AS
SELECT
    d.log_date AS day,
    COUNT(*) AS total_entry_count,
    COALESCE(SUM(d.calories), 0) AS total_calories,
	COUNT(*) FILTER (WHERE LOWER(d.meal) != 'drink') AS food_entry_count,
	COALESCE(SUM(d.calories) FILTER (
        WHERE LOWER(d.meal) != 'drink'
    ), 0) AS food_calories,
    COUNT(*) FILTER (WHERE LOWER(d.meal) = 'drink' AND d.food NOT LIKE 'beer%') AS drink_entry_count,
	COALESCE(SUM(d.calories) FILTER (
        WHERE LOWER(d.meal) = 'drink' AND LOWER(d.food) NOT LIKE 'beer%'
    ), 0) AS drink_calories,
    COUNT(*) FILTER (WHERE LOWER(d.food) LIKE 'beer%') AS alcohol_entry_count,
	COALESCE(SUM(d.calories) FILTER (
        WHERE LOWER(d.meal) = 'drink' AND LOWER(d.food) LIKE 'beer%'
    ), 0) AS alcohol_calories,
    BOOL_OR(LOWER(d.food) LIKE 'beer%') AS had_alcohol,
    ARRAY_REMOVE(ARRAY_AGG(DISTINCT d.meal), NULL) AS meals_logged,
    ARRAY_REMOVE(ARRAY_AGG(DISTINCT d.confidence), NULL) AS confidence_levels,
    ARRAY_AGG(d.food ORDER BY d.id) AS foods_logged
FROM diet d
GROUP BY d.log_date

CREATE OR REPLACE VIEW vw_daily_safety_meeting_summary AS
SELECT
    smd.entry_date AS day,
    TRUE AS safety_meeting
FROM safety_meeting_daily smd;

CREATE OR REPLACE VIEW vw_daily_health_summary AS
WITH weight_daily AS (
    SELECT
        w.entry_date AS day,
        AVG(w.weight)::numeric(6,2) AS avg_weight,
        MIN(w.weight)::numeric(6,2) AS min_weight,
        MAX(w.weight)::numeric(6,2) AS max_weight,
        COUNT(*) AS weight_entry_count
    FROM weight w
    GROUP BY w.entry_date
),
bp_daily AS (
    SELECT
        bp.entry_date AS day,
        AVG(bp.systolic)::numeric(6,2) AS avg_systolic,
        AVG(bp.diastolic)::numeric(6,2) AS avg_diastolic,
        MIN(bp.systolic) AS min_systolic,
        MAX(bp.systolic) AS max_systolic,
        MIN(bp.diastolic) AS min_diastolic,
        MAX(bp.diastolic) AS max_diastolic,
        COUNT(*) AS bp_entry_count
    FROM blood_pressure bp
    GROUP BY bp.entry_date
),
workout_daily AS (
    SELECT
        w.workout_date AS day,
        COUNT(*) AS workout_entry_count,
        COALESCE(SUM(w.calories_burnt), 0) AS total_workout_calories,
        ARRAY_AGG(w.workout ORDER BY w.id) AS workouts_logged
    FROM workout w
    GROUP BY w.workout_date
),
all_days AS (
    SELECT entry_date AS day FROM weight
    UNION
    SELECT entry_date AS day FROM blood_pressure
    UNION
    SELECT workout_date AS day FROM workout
)
SELECT
    ad.day,
    wd.avg_weight,
    wd.min_weight,
    wd.max_weight,
    COALESCE(wd.weight_entry_count, 0) AS weight_entry_count,
    bd.avg_systolic,
    bd.avg_diastolic,
    bd.min_systolic,
    bd.max_systolic,
    bd.min_diastolic,
    bd.max_diastolic,
    COALESCE(bd.bp_entry_count, 0) AS bp_entry_count,
    COALESCE(wod.workout_entry_count, 0) AS workout_entry_count,
    COALESCE(wod.total_workout_calories, 0) AS total_workout_calories,
    COALESCE(wod.workouts_logged, ARRAY[]::text[]) AS workouts_logged,
    (wd.day IS NOT NULL) AS had_weight,
    (bd.day IS NOT NULL) AS had_blood_pressure,
    (wod.day IS NOT NULL) AS had_workout
FROM all_days ad
LEFT JOIN weight_daily wd ON wd.day = ad.day
LEFT JOIN bp_daily bd ON bd.day = ad.day
LEFT JOIN workout_daily wod ON wod.day = ad.day
ORDER BY ad.day;

CREATE OR REPLACE VIEW vw_daily_journal_health AS
WITH journal_daily AS (
    SELECT
        j.entry_date AS day,
        COUNT(*) AS journal_count,
        ARRAY_AGG(j.id ORDER BY j.id) AS journal_ids,
        ARRAY_AGG(j.content ORDER BY j.id) AS journal_contents
    FROM journal j
    GROUP BY j.entry_date
),
journal_analysis_daily AS (
    SELECT
        j.entry_date AS day,
        AVG(jea.mood_score)::numeric(6,2) AS avg_mood_score,
        MIN(jea.mood_score)::numeric(6,2) AS min_mood_score,
        MAX(jea.mood_score)::numeric(6,2) AS max_mood_score,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT jea.emotional_tone), NULL) AS emotional_tones,
        COUNT(jea.id) AS analyzed_journal_count
    FROM journal j
    LEFT JOIN journal_entry_analysis jea
        ON jea.journal_entry_id = j.id
    GROUP BY j.entry_date
),
diet_daily AS (
    SELECT * FROM vw_daily_diet_summary
),
health_daily AS (
    SELECT * FROM vw_daily_health_summary
),
all_days AS (
    SELECT entry_date AS day FROM journal
    UNION
    SELECT log_date AS day FROM diet
    UNION
    SELECT entry_date AS day FROM weight
    UNION
    SELECT entry_date AS day FROM blood_pressure
    UNION
    SELECT workout_date AS day FROM workout
)
SELECT
    ad.day,
    COALESCE(jd.journal_count, 0) AS journal_count,
    COALESCE(jd.journal_ids, ARRAY[]::integer[]) AS journal_ids,
    COALESCE(jd.journal_contents, ARRAY[]::text[]) AS journal_contents,
    jad.avg_mood_score,
    jad.min_mood_score,
    jad.max_mood_score,
    COALESCE(jad.emotional_tones, ARRAY[]::text[]) AS emotional_tones,
    COALESCE(jad.analyzed_journal_count, 0) AS analyzed_journal_count,

	COALESCE(dd.total_entry_count, 0) AS total_entry_count,
	COALESCE(dd.total_calories, 0) AS total_calories,
    COALESCE(dd.food_entry_count, 0) AS food_entry_count,
	COALESCE(dd.food_calories, 0) AS food_calories,
    COALESCE(dd.drink_entry_count, 0) AS drink_entry_count,
	COALESCE(dd.drink_calories, 0) AS drink_calories,
    COALESCE(dd.alcohol_entry_count, 0) AS alcohol_entry_count,
	COALESCE(dd.alcohol_calories, 0) AS alcohol_calories,
    COALESCE(dd.had_alcohol, FALSE) AS had_alcohol,
    COALESCE(dd.meals_logged, ARRAY[]::text[]) AS meals_logged,
    COALESCE(dd.confidence_levels, ARRAY[]::text[]) AS confidence_levels,

    hd.avg_weight,
    hd.min_weight,
    hd.max_weight,
    COALESCE(hd.weight_entry_count, 0) AS weight_entry_count,
    hd.avg_systolic,
    hd.avg_diastolic,
    hd.min_systolic,
    hd.max_systolic,
    hd.min_diastolic,
    hd.max_diastolic,
    COALESCE(hd.bp_entry_count, 0) AS bp_entry_count,
    COALESCE(hd.workout_entry_count, 0) AS workout_entry_count,
    COALESCE(hd.total_workout_calories, 0) AS total_workout_calories,
    COALESCE(hd.workouts_logged, ARRAY[]::text[]) AS workouts_logged,

    (jd.day IS NOT NULL) AS had_journal,
    (jad.analyzed_journal_count > 0) AS had_journal_analysis,
    COALESCE(hd.had_weight, FALSE) AS had_weight,
    COALESCE(hd.had_blood_pressure, FALSE) AS had_blood_pressure,
    COALESCE(hd.had_workout, FALSE) AS had_workout,
    (dd.day IS NOT NULL) AS had_diet
FROM all_days ad
LEFT JOIN journal_daily jd ON jd.day = ad.day
LEFT JOIN journal_analysis_daily jad ON jad.day = ad.day
LEFT JOIN diet_daily dd ON dd.day = ad.day
LEFT JOIN health_daily hd ON hd.day = ad.day
ORDER BY ad.day;

CREATE OR REPLACE VIEW vw_daily_journal_signals AS
WITH base AS (
    SELECT
        j.entry_date AS day,
        j.id AS journal_id,
        jea.id AS analysis_id,
        jea.mood_score,
        jea.emotional_tone,
        jea.key_emotions,
        jea.stressors,
        jea.positive_signals,
        jea.thinking_patterns,
        jea.life_direction_signals,
        jea.reflection_questions
    FROM journal j
    JOIN journal_entry_analysis jea
        ON jea.journal_entry_id = j.id
),
key_emotions_daily AS (
    SELECT
        b.day,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS key_emotions
    FROM base b
    CROSS JOIN LATERAL jsonb_array_elements_text(
        COALESCE(b.key_emotions, '[]'::jsonb)
    ) AS elem
    GROUP BY b.day
),
stressors_daily AS (
    SELECT
        b.day,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS stressors
    FROM base b
    CROSS JOIN LATERAL jsonb_array_elements_text(
        COALESCE(b.stressors, '[]'::jsonb)
    ) AS elem
    GROUP BY b.day
),
positive_signals_daily AS (
    SELECT
        b.day,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS positive_signals
    FROM base b
    CROSS JOIN LATERAL jsonb_array_elements_text(
        COALESCE(b.positive_signals, '[]'::jsonb)
    ) AS elem
    GROUP BY b.day
),
thinking_patterns_daily AS (
    SELECT
        b.day,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS thinking_patterns
    FROM base b
    CROSS JOIN LATERAL jsonb_array_elements_text(
        COALESCE(b.thinking_patterns, '[]'::jsonb)
    ) AS elem
    GROUP BY b.day
),
life_direction_signals_daily AS (
    SELECT
        b.day,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS life_direction_signals
    FROM base b
    CROSS JOIN LATERAL jsonb_array_elements_text(
        COALESCE(b.life_direction_signals, '[]'::jsonb)
    ) AS elem
    GROUP BY b.day
),
reflection_questions_daily AS (
    SELECT
        b.day,
        ARRAY_AGG(elem ORDER BY elem) AS reflection_questions
    FROM base b
    CROSS JOIN LATERAL jsonb_array_elements_text(
        COALESCE(b.reflection_questions, '[]'::jsonb)
    ) AS elem
    GROUP BY b.day
),
daily_core AS (
    SELECT
        b.day,
        COUNT(DISTINCT b.journal_id) AS journal_count,
        COUNT(DISTINCT b.analysis_id) AS analyzed_journal_count,
        AVG(b.mood_score)::numeric(6,2) AS avg_mood_score,
        MIN(b.mood_score)::numeric(6,2) AS min_mood_score,
        MAX(b.mood_score)::numeric(6,2) AS max_mood_score,
        ARRAY_REMOVE(
            ARRAY_AGG(DISTINCT b.emotional_tone),
            NULL
        ) AS emotional_tones
    FROM base b
    GROUP BY b.day
)
SELECT
    dc.day,
    dc.journal_count,
    dc.analyzed_journal_count,
    dc.avg_mood_score,
    dc.min_mood_score,
    dc.max_mood_score,
    COALESCE(dc.emotional_tones, ARRAY[]::text[]) AS emotional_tones,
    COALESCE(ked.key_emotions, ARRAY[]::text[]) AS key_emotions,
    COALESCE(sd.stressors, ARRAY[]::text[]) AS stressors,
    COALESCE(psd.positive_signals, ARRAY[]::text[]) AS positive_signals,
    COALESCE(tpd.thinking_patterns, ARRAY[]::text[]) AS thinking_patterns,
    COALESCE(ldsd.life_direction_signals, ARRAY[]::text[]) AS life_direction_signals,
    COALESCE(rqd.reflection_questions, ARRAY[]::text[]) AS reflection_questions
FROM daily_core dc
LEFT JOIN key_emotions_daily ked
    ON ked.day = dc.day
LEFT JOIN stressors_daily sd
    ON sd.day = dc.day
LEFT JOIN positive_signals_daily psd
    ON psd.day = dc.day
LEFT JOIN thinking_patterns_daily tpd
    ON tpd.day = dc.day
LEFT JOIN life_direction_signals_daily ldsd
    ON ldsd.day = dc.day
LEFT JOIN reflection_questions_daily rqd
    ON rqd.day = dc.day
ORDER BY dc.day;

CREATE OR REPLACE VIEW vw_daily_weather_summary AS
SELECT
    wd.weather_date AS day,
    wd.weather_code,
    wd.weather_summary,
    wd.temp_max_f,
    wd.temp_min_f,
    wd.sunrise,
    wd.sunset,
    wd.moon_phase_percent,
    wd.moon_phase_name,
    (wd.weather_summary ILIKE '%rain%' OR wd.weather_summary ILIKE '%drizzle%' OR wd.weather_summary ILIKE '%mix%') AS had_rain,
    (wd.weather_summary ILIKE '%snow%' OR wd.weather_summary ILIKE '%mix%') AS had_snow,
    (
        wd.weather_summary ILIKE '%cloud%'
        OR wd.weather_summary ILIKE '%overcast%'
    ) AS had_clouds,
    (
        wd.weather_summary ILIKE '%sun%'
        OR wd.weather_summary ILIKE '%clear%'
    ) AS had_sun
FROM weather_daily wd
ORDER BY wd.weather_date;

CREATE OR REPLACE VIEW vw_daily_life_facts AS
WITH all_days AS (
    SELECT entry_date AS day FROM journal
    UNION
    SELECT log_date AS day FROM diet
    UNION
    SELECT entry_date AS day FROM weight
    UNION
    SELECT entry_date AS day FROM blood_pressure
    UNION
    SELECT workout_date AS day FROM workout
    UNION
    SELECT weather_date AS day FROM weather_daily
	UNION
    SELECT entry_date AS day FROM safety_meeting_daily
)
SELECT
    ad.day,

    -- journal / mood
    COALESCE(vdjh.journal_count, 0) AS journal_count,
    vdjh.avg_mood_score,
    vdjh.min_mood_score,
    vdjh.max_mood_score,
    COALESCE(vdjh.had_journal, FALSE) AS had_journal,
    COALESCE(vdjh.had_journal_analysis, FALSE) AS had_journal_analysis,

    -- diet
	COALESCE(vdds.total_entry_count, 0) AS total_entry_count,
	COALESCE(vdds.total_calories, 0) AS total_calories,
    COALESCE(vdds.food_entry_count, 0) AS food_entry_count,
	COALESCE(vdds.food_calories, 0) AS food_calories,
    COALESCE(vdds.drink_entry_count, 0) AS drink_entry_count,
	COALESCE(vdds.drink_calories, 0) AS drink_calories,
    COALESCE(vdds.alcohol_entry_count, 0) AS alcohol_entry_count,
	COALESCE(vdds.alcohol_calories, 0) AS alcohol_calories,
    COALESCE(vdds.had_alcohol, FALSE) AS had_alcohol,

    -- health
    vdhs.avg_weight,
    vdhs.avg_systolic,
    vdhs.avg_diastolic,
    COALESCE(vdhs.workout_entry_count, 0) AS workout_entry_count,
    COALESCE(vdhs.total_workout_calories, 0) AS total_workout_calories,
    COALESCE(vdhs.had_weight, FALSE) AS had_weight,
    COALESCE(vdhs.had_blood_pressure, FALSE) AS had_blood_pressure,
    COALESCE(vdhs.had_workout, FALSE) AS had_workout,

    -- weather
    vdws.weather_code,
    vdws.weather_summary,
    vdws.temp_max_f,
    vdws.temp_min_f,
    vdws.sunrise,
    vdws.sunset,
    vdws.moon_phase_percent,
    vdws.moon_phase_name,
    COALESCE(vdws.had_rain, FALSE) AS had_rain,
    COALESCE(vdws.had_snow, FALSE) AS had_snow,
    COALESCE(vdws.had_clouds, FALSE) AS had_clouds,
    COALESCE(vdws.had_sun, FALSE) AS had_sun,

	--safety meeting
	COALESCE(vdsms.safety_meeting, FALSE) AS safety_meeting,
	
    -- convenience fields
    CASE
        WHEN vdws.temp_max_f IS NULL THEN NULL
        WHEN vdws.temp_max_f < 32 THEN 'freezing'
        WHEN vdws.temp_max_f < 50 THEN 'cold'
        WHEN vdws.temp_max_f < 70 THEN 'mild'
        WHEN vdws.temp_max_f < 85 THEN 'warm'
        ELSE 'hot'
    END AS temp_band
FROM all_days ad
LEFT JOIN vw_daily_journal_health vdjh
    ON vdjh.day = ad.day
LEFT JOIN vw_daily_diet_summary vdds
    ON vdds.day = ad.day
LEFT JOIN vw_daily_health_summary vdhs
    ON vdhs.day = ad.day
LEFT JOIN vw_daily_weather_summary vdws
    ON vdws.day = ad.day
LEFT JOIN vw_daily_safety_meeting_summary vdsms
    ON vdsms.day = ad.day
ORDER BY ad.day;

CREATE OR REPLACE VIEW vw_weekly_life_summary AS
WITH daily AS (
    SELECT
        vdlf.day,
        date_trunc('week', vdlf.day)::date AS week_start,
        (date_trunc('week', vdlf.day)::date + INTERVAL '6 days')::date AS week_end,

        -- journal / mood
        vdlf.journal_count,
        vdlf.avg_mood_score,
        vdlf.min_mood_score,
        vdlf.max_mood_score,
        vdlf.had_journal,
        vdlf.had_journal_analysis,

        -- diet
		vdlf.total_entry_count,
		vdlf.total_calories,
        vdlf.food_entry_count,
		vdlf.food_calories,
        vdlf.drink_entry_count,
		vdlf.drink_calories,
        vdlf.alcohol_entry_count,
		vdlf.alcohol_calories,
        vdlf.had_alcohol,

        -- health
        vdlf.avg_weight,
        vdlf.avg_systolic,
        vdlf.avg_diastolic,
        vdlf.workout_entry_count,
        vdlf.total_workout_calories,
        vdlf.had_weight,
        vdlf.had_blood_pressure,
        vdlf.had_workout,

        -- weather
        vdlf.weather_summary,
        vdlf.temp_max_f,
        vdlf.temp_min_f,
        vdlf.had_rain,
        vdlf.had_snow,
        vdlf.had_clouds,
        vdlf.had_sun,
        vdlf.temp_band,

        -- safety meeting
        vdlf.safety_meeting

    FROM vw_daily_life_facts vdlf
),
signal_arrays AS (
    SELECT
        vdjs.day,
        date_trunc('week', vdjs.day)::date AS week_start,
        vdjs.key_emotions,
        vdjs.stressors,
        vdjs.positive_signals,
        vdjs.thinking_patterns,
        vdjs.life_direction_signals
    FROM vw_daily_journal_signals vdjs
),
weekly_core AS (
    SELECT
        d.week_start,
        MAX(d.week_end) AS week_end,

        COUNT(*) AS days_in_week,

        -- journal / mood
        SUM(d.journal_count) AS journal_count,
        COUNT(*) FILTER (WHERE d.had_journal) AS days_with_journal,
        COUNT(*) FILTER (WHERE d.had_journal_analysis) AS days_with_journal_analysis,
        AVG(d.avg_mood_score)::numeric(6,2) AS avg_mood_score,
        MIN(d.min_mood_score)::numeric(6,2) AS min_mood_score,
        MAX(d.max_mood_score)::numeric(6,2) AS max_mood_score,

        -- diet
		SUM(d.total_entry_count) AS total_entry_count,
		SUM(d.total_calories)::numeric(10,2) AS total_calories,
		AVG(d.total_calories)::numeric(10,2) AS avg_daily_calories,		
        SUM(d.food_entry_count) AS food_entry_count,
		SUM(d.food_calories)::numeric(10,2) AS food_total_calories,
        AVG(d.food_calories)::numeric(10,2) AS food_avg_daily_calories,
        SUM(d.drink_entry_count) AS drink_entry_count,
		SUM(d.drink_calories) AS drink_total_calories,
		AVG(d.drink_calories)::numeric(10,2) AS drink_avg_daily_calories,
        SUM(d.alcohol_entry_count) AS alc_entry_count,
		SUM(d.alcohol_calories) AS alc_total_calories,
		AVG(d.alcohol_calories)::numeric(10,2) AS alc_avg_daily_calories,
        COUNT(*) FILTER (WHERE d.had_alcohol) AS alcohol_days,

        -- health
        AVG(d.avg_weight)::numeric(8,2) AS avg_weight,
        MIN(d.avg_weight)::numeric(8,2) AS min_weight,
        MAX(d.avg_weight)::numeric(8,2) AS max_weight,
        AVG(d.avg_systolic)::numeric(8,2) AS avg_systolic,
        AVG(d.avg_diastolic)::numeric(8,2) AS avg_diastolic,
        SUM(d.workout_entry_count) AS workout_entry_count,
        SUM(d.total_workout_calories)::numeric(10,2) AS total_workout_calories,
        AVG(d.total_workout_calories)::numeric(10,2) AS avg_daily_workout_calories,
        COUNT(*) FILTER (WHERE d.had_workout) AS workout_days,

        -- weather
        AVG(d.temp_max_f)::numeric(8,2) AS avg_temp_max_f,
        AVG(d.temp_min_f)::numeric(8,2) AS avg_temp_min_f,
        MAX(d.temp_max_f)::numeric(8,2) AS hottest_temp_f,
        MIN(d.temp_min_f)::numeric(8,2) AS coldest_temp_f,
        COUNT(*) FILTER (WHERE d.had_rain) AS rain_days,
        COUNT(*) FILTER (WHERE d.had_snow) AS snow_days,
        COUNT(*) FILTER (WHERE d.had_clouds) AS cloudy_days,
        COUNT(*) FILTER (WHERE d.had_sun) AS sunny_days,

        -- safety meeting
        COUNT(*) FILTER (WHERE d.safety_meeting) AS safety_meeting_days

    FROM daily d
    GROUP BY d.week_start
),
weather_rollup AS (
    SELECT
        d.week_start,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT d.weather_summary), NULL) AS weather_summaries,
        ARRAY_REMOVE(ARRAY_AGG(DISTINCT d.temp_band), NULL) AS temp_bands
    FROM daily d
    GROUP BY d.week_start
),
key_emotions_weekly AS (
    SELECT
        sa.week_start,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS key_emotions
    FROM signal_arrays sa
    CROSS JOIN LATERAL unnest(
        COALESCE(sa.key_emotions, ARRAY[]::text[])
    ) AS elem
    GROUP BY sa.week_start
),
stressors_weekly AS (
    SELECT
        sa.week_start,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS stressors
    FROM signal_arrays sa
    CROSS JOIN LATERAL unnest(
        COALESCE(sa.stressors, ARRAY[]::text[])
    ) AS elem
    GROUP BY sa.week_start
),
positive_signals_weekly AS (
    SELECT
        sa.week_start,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS positive_signals
    FROM signal_arrays sa
    CROSS JOIN LATERAL unnest(
        COALESCE(sa.positive_signals, ARRAY[]::text[])
    ) AS elem
    GROUP BY sa.week_start
),
thinking_patterns_weekly AS (
    SELECT
        sa.week_start,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS thinking_patterns
    FROM signal_arrays sa
    CROSS JOIN LATERAL unnest(
        COALESCE(sa.thinking_patterns, ARRAY[]::text[])
    ) AS elem
    GROUP BY sa.week_start
),
life_direction_signals_weekly AS (
    SELECT
        sa.week_start,
        ARRAY_AGG(DISTINCT elem ORDER BY elem) AS life_direction_signals
    FROM signal_arrays sa
    CROSS JOIN LATERAL unnest(
        COALESCE(sa.life_direction_signals, ARRAY[]::text[])
    ) AS elem
    GROUP BY sa.week_start
)
SELECT
    wc.week_start,
    wc.week_end,

    wc.days_in_week,

    -- journal / mood
    wc.journal_count,
    wc.days_with_journal,
    wc.days_with_journal_analysis,
    wc.avg_mood_score,
    wc.min_mood_score,
    wc.max_mood_score,

    -- diet
	wc.total_entry_count,
	wc.total_calories,
	wc.avg_daily_calories,
    wc.food_entry_count,
	wc.food_total_calories,
    wc.food_avg_daily_calories,
    wc.drink_entry_count,
    wc.drink_total_calories,
    wc.drink_avg_daily_calories,
	wc.alc_entry_count,
    wc.alc_total_calories,
    wc.alc_avg_daily_calories,
	wc.alcohol_days,

    -- health
    wc.avg_weight,
    wc.min_weight,
    wc.max_weight,
    wc.avg_systolic,
    wc.avg_diastolic,
    wc.workout_entry_count,
    wc.total_workout_calories,
    wc.avg_daily_workout_calories,
    wc.workout_days,

    -- convenience metric
    (wc.total_calories - wc.total_workout_calories)::numeric(10,2) AS net_calories,

    -- weather
    wc.avg_temp_max_f,
    wc.avg_temp_min_f,
    wc.hottest_temp_f,
    wc.coldest_temp_f,
    wc.rain_days,
    wc.snow_days,
    wc.cloudy_days,
    wc.sunny_days,
    COALESCE(wr.weather_summaries, ARRAY[]::text[]) AS weather_summaries,
    COALESCE(wr.temp_bands, ARRAY[]::text[]) AS temp_bands,

    -- safety meeting
    wc.safety_meeting_days,

    -- signals
    COALESCE(kew.key_emotions, ARRAY[]::text[]) AS key_emotions,
    COALESCE(sw.stressors, ARRAY[]::text[]) AS stressors,
    COALESCE(psw.positive_signals, ARRAY[]::text[]) AS positive_signals,
    COALESCE(tpw.thinking_patterns, ARRAY[]::text[]) AS thinking_patterns,
    COALESCE(ldsw.life_direction_signals, ARRAY[]::text[]) AS life_direction_signals

FROM weekly_core wc
LEFT JOIN weather_rollup wr
    ON wr.week_start = wc.week_start
LEFT JOIN key_emotions_weekly kew
    ON kew.week_start = wc.week_start
LEFT JOIN stressors_weekly sw
    ON sw.week_start = wc.week_start
LEFT JOIN positive_signals_weekly psw
    ON psw.week_start = wc.week_start
LEFT JOIN thinking_patterns_weekly tpw
    ON tpw.week_start = wc.week_start
LEFT JOIN life_direction_signals_weekly ldsw
    ON ldsw.week_start = wc.week_start
ORDER BY wc.week_start;