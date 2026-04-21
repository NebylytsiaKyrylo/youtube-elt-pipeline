DROP TABLE IF EXISTS marts.mart_channel_latest_videos;
CREATE TABLE marts.mart_channel_latest_videos AS
WITH
latest_video_per_channel AS (
    SELECT
        dc.channel_name,
        dv.title,
        dv.published_at,
        MAX(dv.published_at) OVER (PARTITION BY dc.channel_key) AS latest_published_at
    FROM core.dim_video AS dv
    INNER JOIN core.dim_channel AS dc
        ON dv.channel_key = dc.channel_key
)

SELECT
    channel_name,
    title AS latest_title,
    latest_published_at,
    CURRENT_DATE - latest_published_at::DATE AS days_since_last_video
FROM latest_video_per_channel
WHERE
    published_at = latest_published_at
ORDER BY
    days_since_last_video;
