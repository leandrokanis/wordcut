-- 1.2.a.1: the team. Of personal data, only the e-mail is kept (LGPD, constitution §VI),
-- in lower case without surrounding spaces; the service normalizes it before every query.
-- The service keeps at least one admin once the first exists (FR-003).
CREATE TABLE members (
    email TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('assistant', 'admin')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
