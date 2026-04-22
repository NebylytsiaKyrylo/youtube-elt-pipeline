DROP TABLE IF EXISTS marts.mart_channel_top_subscribers;
CREATE TABLE marts.mart_channel_top_subscribers AS
SELECT
    dc.channel_name,
    dc.subscribers_count,
    SUM(ds.video_views) AS total_views,
    COUNT(ds.video_key) AS total_videos
FROM core.fct_video_daily_snapshot AS ds
INNER JOIN core.dim_channel AS dc
    ON ds.channel_key = dc.channel_key
WHERE
    ds.snapshot_date = '{{ ds }}'::DATE
GROUP BY
    dc.channel_name,
    dc.subscribers_count
ORDER BY
    dc.subscribers_count DESC;
