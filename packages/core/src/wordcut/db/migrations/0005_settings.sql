-- 2.1.a.1: configuration shared by every adapter, as key and value. Secrets never go here:
-- they are files of the configuration folder (wordcut.config, constitution §VI).
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
