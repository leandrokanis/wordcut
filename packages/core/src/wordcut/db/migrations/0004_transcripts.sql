-- 1.1.c.1: the processed sermon. Borders fitted to the words (sermon_start, sermon_end) are
-- in live time; video_path is relative to the data folder; words and sentences are in
-- sermon time (docs/cli.md §3.4).
ALTER TABLE sermons ADD COLUMN sermon_start REAL;
ALTER TABLE sermons ADD COLUMN sermon_end REAL;
ALTER TABLE sermons ADD COLUMN video_path TEXT;
ALTER TABLE sermons ADD COLUMN processed_at TEXT;

-- AUTOINCREMENT: a word_id is never reused after a reprocess (docs/cli.md §3.3).
CREATE TABLE words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sermon_id INTEGER NOT NULL REFERENCES sermons (id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    start REAL NOT NULL,
    "end" REAL NOT NULL,
    score REAL,
    estimated INTEGER NOT NULL CHECK (estimated IN (0, 1)),
    UNIQUE (sermon_id, position)
);

CREATE TABLE sentences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sermon_id INTEGER NOT NULL REFERENCES sermons (id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    first_word_id INTEGER NOT NULL REFERENCES words (id),
    last_word_id INTEGER NOT NULL REFERENCES words (id),
    start REAL NOT NULL,
    "end" REAL NOT NULL,
    text TEXT NOT NULL,
    UNIQUE (sermon_id, position)
);
