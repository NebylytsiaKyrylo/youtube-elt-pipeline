DROP TABLE IF EXISTS marts.mart_channel_retention;
CREATE TABLE marts.mart_channel_retention AS

WITH
aggregated_channel_active AS (

    SELECT
        dc.channel_key,
        dc.channel_name,
        MAX(dv.published_at) AS last_published,
        COUNT(dv.video_id) AS total_videos,
        SUM(ds.video_views) AS total_views,
        SUM(ds.video_likes) AS total_likes,
        SUM(ds.video_comments) AS total_comments
    FROM core.fct_video_daily_snapshot AS ds
    INNER JOIN core.dim_channel AS dc
        ON ds.channel_key = dc.channel_key
    INNER JOIN core.dim_video AS dv
        ON ds.video_key = dv.video_key
    WHERE
        ds.snapshot_date = CURRENT_DATE
    GROUP BY
        dc.channel_key,
        dc.channel_name
    HAVING
        MAX(dv.published_at) > CURRENT_DATE - 30 * INTERVAL '1 day'
)

SELECT
    channel_name,
    total_videos,
    total_views,
    total_comments,
    ROUND(total_comments::NUMERIC / total_views, 3) AS retention_score,
    ROUND((total_likes + total_comments)::NUMERIC / total_views, 3) AS engagement_score
FROM aggregated_channel_active
ORDER BY
    retention_score DESC;
