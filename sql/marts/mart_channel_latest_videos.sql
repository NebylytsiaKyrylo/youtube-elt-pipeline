DROP TABLE IF EXISTS marts.mart_channel_latest_videos;
CREATE TABLE marts.mart_channel_latest_videos AS
SELECT DISTINCT ON (dc.channel_key)
    dc.channel_name,
    dv.title AS latest_title,
    dv.published_at AS latest_published_at,
    '{{ ds }}'::DATE - dv.published_at::DATE AS days_since_last_video
FROM core.dim_video AS dv
INNER JOIN core.dim_channel AS dc
    ON dv.channel_key = dc.channel_key
ORDER BY
    dc.channel_key,
    dv.published_at DESC;
