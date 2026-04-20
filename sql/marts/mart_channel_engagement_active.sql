DROP TABLE IF EXISTS marts.mart_channel_engagement_active;
CREATE TABLE marts.mart_channel_engagement_active AS

WITH
aggregated_channel_active AS (

    SELECT
        dc.channel_key,
        dc.channel_name AS channel_title,
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, dc.channel_start_date)) AS channel_age_years,
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
        dc.channel_name,
        channel_age_years
    HAVING
        MAX(dv.published_at) > CURRENT_DATE - 30 * INTERVAL '1 day'
)

SELECT
    channel_title,
    channel_age_years,
    last_published,
    total_videos,
    total_views,
    total_likes,
    total_comments,
    ROUND((total_likes + total_comments)::NUMERIC / total_views, 3) AS engagement_score
FROM aggregated_channel_active
ORDER BY
    engagement_score DESC;
