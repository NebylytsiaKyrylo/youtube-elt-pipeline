-- 1. dim_channel before dim_video: FK in dim_video references channel_key
INSERT INTO core.dim_channel (
    channel_id,
    channel_name,
    subscribers_count,
    channel_start_date
)
-- DISTINCT: staging has one row per video, multiple rows per channel
SELECT DISTINCT
    channel_id::VARCHAR(24),
    channel_name,
    subscribers_count::BIGINT,
    channel_start_date::DATE
FROM staging.yt_video_snapshot
ON CONFLICT (channel_id) DO UPDATE
    SET
        channel_name = excluded.channel_name,
        subscribers_count = excluded.subscribers_count,
        updated_at = NOW();

-- 2. dim_video: FK in dim_video references channel_key
INSERT INTO core.dim_video (
    video_id,
    channel_key,
    title,
    published_at,
    duration_seconds
)
SELECT
    yvs.video_id::VARCHAR(11),
    dc.channel_key,
    yvs.title,
    yvs.published_at::TIMESTAMPTZ,
    EXTRACT(EPOCH FROM yvs.duration_iso::INTERVAL)::INT AS duration_seconds
FROM staging.yt_video_snapshot AS yvs
INNER JOIN core.dim_channel AS dc
    ON yvs.channel_id = dc.channel_id
WHERE EXTRACT(EPOCH FROM yvs.duration_iso::INTERVAL)::INT > 0
ON CONFLICT (video_id) DO UPDATE
    SET
        title = excluded.title,
        duration_seconds = excluded.duration_seconds,
        updated_at = NOW();

-- 3. fct_video_daily_snapshot: FK in fct_video_daily_snapshot references video_key and channel_key
INSERT INTO core.fct_video_daily_snapshot (
    video_key,
    channel_key,
    snapshot_date,
    video_views,
    video_likes,
    video_comments,
    ingestion_ts
)
SELECT
    dv.video_key,
    dc.channel_key,
    '{{ ds }}'::DATE AS snapshot_date,
    yvs.view_count::BIGINT AS video_views,
    yvs.like_count::BIGINT AS video_likes,
    yvs.comment_count::BIGINT AS video_comments,
    NOW() AS ingestion_ts
FROM staging.yt_video_snapshot AS yvs
INNER JOIN core.dim_channel AS dc
    ON yvs.channel_id = dc.channel_id
INNER JOIN core.dim_video AS dv
    ON yvs.video_id = dv.video_id
WHERE EXTRACT(EPOCH FROM yvs.duration_iso::INTERVAL)::INT > 0
ON CONFLICT (video_key, snapshot_date) DO UPDATE
    SET
        video_views = excluded.video_views,
        video_likes = excluded.video_likes,
        video_comments = excluded.video_comments,
        ingestion_ts = excluded.ingestion_ts;
