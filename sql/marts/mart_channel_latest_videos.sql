CREATE TABLE marts.mart_channel_latest_videos_new AS
SELECT DISTINCT ON (dc.channel_key)
    dc.channel_name,
    dv.title AS latest_title,
    dv.published_at AS latest_published_at,
    '{{ ds }}'::DATE - dv.published_at::DATE AS days_since_last_video
FROM core.dim_video AS dv
INNER JOIN core.dim_channel AS dc
    ON dv.channel_key = dc.channel_key
WHERE dv.is_active = TRUE
ORDER BY
    dc.channel_key ASC,
    dv.published_at DESC;

ALTER TABLE IF EXISTS marts.mart_channel_latest_videos RENAME TO mart_channel_latest_videos_old;
ALTER TABLE marts.mart_channel_latest_videos_new RENAME TO mart_channel_latest_videos;
DROP TABLE IF EXISTS marts.mart_channel_latest_videos_old;