-- AUTOINCREMENT: an ID is never reused after a delete, so it stays stable (docs/cli.md §3.3).
CREATE TABLE sermons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    youtube_id TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    service_date TEXT NOT NULL,
    live_duration REAL,
    live_finished INTEGER NOT NULL CHECK (live_finished IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'created'
        CHECK (status IN ('created', 'trimmed', 'processing', 'processed', 'failed')),
    live_start REAL,
    live_end REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
