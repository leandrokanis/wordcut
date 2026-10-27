-- 1.1.b.3: the live borders of the last successful processing, null until a sermon is
-- processed. Sermons processed before this migration take their current borders as the
-- processed ones (FR-004), so they show no border change until the next trim.
ALTER TABLE sermons ADD COLUMN processed_live_start REAL;
ALTER TABLE sermons ADD COLUMN processed_live_end REAL;
UPDATE sermons SET processed_live_start = live_start, processed_live_end = live_end
WHERE status = 'processed';
