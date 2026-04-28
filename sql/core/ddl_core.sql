CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.dim_channel (
    channel_key SERIAL PRIMARY KEY,
    channel_id VARCHAR(24) NOT NULL UNIQUE,
    channel_name TEXT,
    subscribers_count BIGINT,
    channel_start_date DATE,
    loaded_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.dim_video (
    video_key SERIAL PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL UNIQUE,
    channel_key INT NOT NULL REFERENCES core.dim_channel (channel_key),
    title TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    duration_seconds INT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    loaded_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.fct_video_daily_snapshot (
    video_key INT NOT NULL REFERENCES core.dim_video (video_key),
    channel_key INT NOT NULL REFERENCES core.dim_channel (channel_key),
    snapshot_date DATE NOT NULL,
    video_views BIGINT,
    video_likes BIGINT,
    video_comments BIGINT,
    ingestion_ts TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (video_key, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_fct_channel
ON core.fct_video_daily_snapshot (channel_key, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_dim_video_deleted
ON core.dim_video (video_key)
WHERE is_active = FALSE;
