/*
This script creates the staging schema and table.
*/

-- Create staging schema
CREATE SCHEMA IF NOT EXISTS staging;

-- Create staging table
CREATE TABLE IF NOT EXISTS staging.yt_video_snapshot (
    video_id           TEXT        NOT NULL,
    channel_id         TEXT        NOT NULL,
    channel_name       TEXT,
    channel_start_date TEXT,
    title              TEXT,
    published_at       TEXT,
    duration_iso       TEXT,
    view_count         TEXT,
    like_count         TEXT,
    comment_count      TEXT,
    ingestion_ts       TIMESTAMPTZ NOT NULL,
    run_id             TEXT        NOT NULL
);
