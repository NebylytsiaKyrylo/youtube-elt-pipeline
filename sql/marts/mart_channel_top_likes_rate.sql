DROP TABLE IF EXISTS marts.mart_channel_top_likes_rate;
CREATE TABLE marts.mart_channel_top_likes_rate AS
WITH
aggregated_channels AS (
    SELECT
        dc.channel_key,
        dc.channel_name,
        SUM(ds.video_views) AS total_views,
        SUM(ds.video_likes) AS total_likes
    FROM core.fct_video_daily_snapshot AS ds
    INNER JOIN core.dim_channel AS dc
        ON ds.channel_key = dc.channel_key
    WHERE
        ds.snapshot_date = CURRENT_DATE
    GROUP BY
        dc.channel_key,
        dc.channel_name
    HAVING SUM(ds.video_views) >= 10000
)

SELECT
    channel_name,
    total_views,
    total_likes,
    ROUND(total_likes::NUMERIC / total_views, 3) AS likes_rate
FROM aggregated_channels
ORDER BY likes_rate DESC;
