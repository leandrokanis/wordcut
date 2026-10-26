-- 1.1.h.1: the exports of a cut. path is relative to the data folder and names the file
-- after the export's ID; AUTOINCREMENT never gives an ID twice, so a file name never repeats
-- even after its cut is gone. options is JSON, the nine choices of docs/cli.md §8.7.
-- ON DELETE CASCADE: sermon suggest, reprocessing and sermon delete remove cuts.
CREATE TABLE renders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cut_id INTEGER NOT NULL REFERENCES cuts (id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    duration REAL NOT NULL,
    options TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX renders_of_cut ON renders (cut_id);
