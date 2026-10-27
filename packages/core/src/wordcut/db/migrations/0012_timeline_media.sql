-- 1.1.b.1: the state of the last preparation of a sermon's timeline media (thumbnails and
-- waveform). A sermon without a row was never prepared, as every sermon created before this
-- migration; the service shows it as failed, to be prepared again.
CREATE TABLE timeline_media (
    sermon_id INTEGER PRIMARY KEY REFERENCES sermons (id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'ready', 'failed')),
    error_code TEXT,
    error_message TEXT,
    updated_at TEXT NOT NULL
);
