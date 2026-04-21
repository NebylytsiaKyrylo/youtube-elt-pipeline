DROP TABLE IF EXISTS marts.mart_channel_size_distribution;
CREATE TABLE marts.mart_channel_size_distribution AS
WITH
aggregated_channels AS (
    SELECT
        ds.channel_key,
        dc.subscribers_count,
        ROUND((SUM(ds.video_likes) + SUM(ds.video_comments))::NUMERIC / SUM(ds.video_views), 3) AS engagement_score,
        CASE
            WHEN SUM(ds.video_views) < 1000000 THEN '< 1M views'
            WHEN SUM(ds.video_views) < 10000000 THEN '1M-10M views'
            WHEN SUM(ds.video_views) < 50000000 THEN '10M-50M views'
            ELSE '> 50M views'
        END AS size_bucket
    FROM core.fct_video_daily_snapshot AS ds
    INNER JOIN core.dim_channel AS dc
        ON ds.channel_key = dc.channel_key
    WHERE
        ds.snapshot_date = CURRENT_DATE
    GROUP BY
        ds.channel_key,
        dc.subscribers_count
)

SELECT
    size_bucket,
    AVG(subscribers_count)::INT AS avg_subscribers_count,
    COUNT(*) AS channel_count,
    ROUND(AVG(engagement_score), 3) AS avg_engagement_score
FROM aggregated_channels
GROUP BY
    size_bucket
ORDER BY
    CASE size_bucket
        WHEN '< 1M views' THEN 1
        WHEN '1M-10M views' THEN 2
        WHEN '10M-50M views' THEN 3
        WHEN '> 50M views' THEN 4
    END
