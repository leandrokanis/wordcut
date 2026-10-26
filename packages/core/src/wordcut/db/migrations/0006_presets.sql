-- 2.1.a.2: presets of the cut suggestion. levels is JSON {criterion_id: level}, completed
-- with the catalog's default levels on reading (FR-006), so the factory preset stores '{}'.
-- protected_words is a JSON list of strings. Durations are whole seconds.
CREATE TABLE presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    levels TEXT NOT NULL,
    duration_allowed_min INTEGER NOT NULL,
    duration_allowed_max INTEGER NOT NULL,
    duration_ideal_min INTEGER NOT NULL,
    duration_ideal_max INTEGER NOT NULL,
    reorder INTEGER NOT NULL CHECK (reorder IN (0, 1)),
    protected_words TEXT NOT NULL,
    instructions TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
-- FR-005: at most one default preset; the service keeps it at exactly one.
CREATE UNIQUE INDEX presets_single_default ON presets (is_default) WHERE is_default = 1;
INSERT INTO presets (
    name, is_default, levels, duration_allowed_min, duration_allowed_max,
    duration_ideal_min, duration_ideal_max, reorder, protected_words, instructions,
    created_at, updated_at
) VALUES (
    'Padrão', 1, '{}', 40, 75, 55, 65, 1, '["não", "mas", "se"]', '',
    strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'), strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now')
);
