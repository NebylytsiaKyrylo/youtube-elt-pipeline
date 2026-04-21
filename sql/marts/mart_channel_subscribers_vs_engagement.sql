DROP TABLE IF EXISTS marts.mart_channel_subscribers_vs_engagement;
CREATE TABLE marts.mart_channel_subscribers_vs_engagement AS
SELECT
    dc.channel_name,
    dc.subscribers_count,
    SUM(ds.video_views) AS total_views,
    ROUND((SUM(ds.video_likes) + SUM(ds.video_comments))::NUMERIC / SUM(ds.video_views), 3) AS engagement_score,
    ROUND((SUM(ds.video_likes) + SUM(ds.video_comments))::NUMERIC / dc.subscribers_count, 3)
        AS engagement_per_subscriber
FROM core.fct_video_daily_snapshot AS ds
INNER JOIN core.dim_channel AS dc
    ON ds.channel_key = dc.channel_key
INNER JOIN
    core.dim_video AS dv
    ON ds.video_key = dv.video_key
WHERE
    ds.snapshot_date = CURRENT_DATE
GROUP BY dc.channel_name, dc.subscribers_count
HAVING
    MAX(dv.published_at) > CURRENT_DATE - 30 * INTERVAL '1 day'
ORDER BY engagement_per_subscriber DESC;
