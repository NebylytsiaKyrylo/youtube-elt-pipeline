CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.yt_video_snapshot (
    video_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    subscribers_count TEXT,
    channel_start_date TEXT,
    title TEXT,
    published_at TEXT,
    duration_iso TEXT,
    view_count TEXT,
    like_count TEXT,
    comment_count TEXT
);
