-- docs/cli.md §6: heavy operations run as tasks. params, result and error_details are JSON.
-- No CHECK on kind: the internal diagnostic kind also lives here (plan of 3.1.a.2).
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id INTEGER NOT NULL,
    params TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    progress REAL NOT NULL DEFAULT 0,
    progress_message TEXT,
    pid INTEGER NOT NULL,
    host TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    error_code TEXT,
    error_message TEXT,
    error_details TEXT,
    result TEXT
);
CREATE INDEX tasks_by_status ON tasks (status);
