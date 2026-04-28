WITH
videos_to_delete AS (
    SELECT dv.video_key
    FROM core.dim_video AS dv
    LEFT JOIN core.fct_video_daily_snapshot AS fct
        ON
            dv.video_key = fct.video_key
            AND fct.snapshot_date = '{{ ds }}'::DATE
    WHERE
        fct.video_key IS NULL
        AND dv.is_active = TRUE
)

UPDATE core.dim_video AS dv
SET
    is_active = FALSE,
    deleted_at = NOW()
FROM videos_to_delete AS vtd
WHERE
    dv.video_key = vtd.video_key;
