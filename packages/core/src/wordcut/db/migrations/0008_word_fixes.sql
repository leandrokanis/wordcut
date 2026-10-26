-- 1.1.f.2: spelling fixes of caption words, each valid only in its cut. text is the fixed
-- spelling; the transcript keeps the original. ON DELETE CASCADE on both keys: reprocessing,
-- sermon suggest and sermon delete remove cuts and words that may carry fixes.
CREATE TABLE word_fixes (
    cut_id INTEGER NOT NULL REFERENCES cuts (id) ON DELETE CASCADE,
    word_id INTEGER NOT NULL REFERENCES words (id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (cut_id, word_id)
);
CREATE INDEX word_fixes_of_word ON word_fixes (word_id);
