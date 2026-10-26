-- 2.1.b.1: the cuts of a sermon. segments is JSON [{"from_word", "to_word"}] in play order;
-- range_start_word and range_end_word bound the continuous range in sermon order (2.1.c).
-- Word IDs live in JSON too, so none of them is a foreign key: reprocessing deletes the cuts
-- together with the words. caption and render_options are JSON, null until edited.
-- ON DELETE SET NULL: deleting an old preset keeps the cuts it suggested (2.1.b.3).
CREATE TABLE cuts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sermon_id INTEGER NOT NULL REFERENCES sermons (id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('suggested', 'chosen', 'discarded')),
    title TEXT NOT NULL,
    segments TEXT NOT NULL,
    range_start_word INTEGER NOT NULL,
    range_end_word INTEGER NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('llm', 'admin')),
    preset_id INTEGER REFERENCES presets (id) ON DELETE SET NULL,
    edited INTEGER NOT NULL DEFAULT 0 CHECK (edited IN (0, 1)),
    caption TEXT,
    render_options TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX cuts_of_sermon ON cuts (sermon_id);

-- The last suggestion's failure, both null when it succeeded or never ran (docs/cli.md §7.2).
ALTER TABLE sermons ADD COLUMN suggestion_error_code TEXT;
ALTER TABLE sermons ADD COLUMN suggestion_error_message TEXT;
