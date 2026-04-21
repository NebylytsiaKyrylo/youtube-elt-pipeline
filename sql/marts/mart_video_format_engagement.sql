DROP TABLE IF EXISTS marts.mart_video_format_engagement;
CREATE TABLE marts.mart_video_format_engagement AS
SELECT
    CASE
        WHEN dv.duration_seconds::NUMERIC / 60 < 3 THEN '0-3 min'
        WHEN dv.duration_seconds::NUMERIC / 60 < 7 THEN '3-7 min'
        WHEN dv.duration_seconds::NUMERIC / 60 < 15 THEN '7-15 min'
        WHEN dv.duration_seconds::NUMERIC / 60 < 30 THEN '15-30 min'
        ELSE '30+ min'
    END AS duration_bucket,
    COUNT(*) AS total_videos,
    ROUND(AVG(ds.video_views)) AS avg_views,
    ROUND((SUM(ds.video_likes) + SUM(ds.video_comments))::NUMERIC / SUM(ds.video_views), 3) AS avg_engagement_score
FROM core.fct_video_daily_snapshot AS ds
INNER JOIN core.dim_video AS dv
    ON ds.video_key = dv.video_key
WHERE
    ds.snapshot_date = CURRENT_DATE
GROUP BY duration_bucket
ORDER BY avg_engagement_score DESC;
