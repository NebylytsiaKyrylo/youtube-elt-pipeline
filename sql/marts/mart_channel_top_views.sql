DROP TABLE IF EXISTS marts.mart_channel_top_views;
CREATE TABLE marts.mart_channel_top_views AS
SELECT
    dc.channel_key,
    dc.channel_name,
    COUNT(ds.video_key) AS total_videos,
    SUM(ds.video_views) AS total_views,
    SUM(ds.video_likes) AS total_likes,
    SUM(ds.video_comments) AS total_comments
FROM core.fct_video_daily_snapshot AS ds
INNER JOIN core.dim_channel AS dc
    ON ds.channel_key = dc.channel_key
WHERE
    ds.snapshot_date = '{{ ds }}'::DATE
GROUP BY
    dc.channel_key,
    dc.channel_name
ORDER BY
    total_views DESC;
