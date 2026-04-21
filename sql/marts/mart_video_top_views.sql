DROP TABLE IF EXISTS marts.mart_video_top_views;
CREATE TABLE marts.mart_video_top_views AS
WITH
ranked_videos AS (
    SELECT
        dc.channel_name,
        dv.title,
        dv.published_at,
        ds.video_views,
        ds.video_likes,
        DENSE_RANK() OVER (ORDER BY ds.video_views DESC) AS video_rank
    FROM core.fct_video_daily_snapshot AS ds
    INNER JOIN core.dim_video AS dv
        ON ds.video_key = dv.video_key
    INNER JOIN core.dim_channel AS dc
        ON ds.channel_key = dc.channel_key
    WHERE
        ds.snapshot_date = CURRENT_DATE
)

SELECT
    channel_name,
    title,
    published_at,
    video_views,
    video_likes
FROM ranked_videos
WHERE
    video_rank BETWEEN 1 AND 10;
