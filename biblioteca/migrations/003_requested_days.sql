ALTER TABLE requests ADD COLUMN requested_days INTEGER
 CHECK(requested_days IS NULL OR (typeof(requested_days)='integer' AND requested_days >= 1
 AND requested_days <= CASE collection_id WHEN 'alta_demanda' THEN 14 ELSE 30 END));
UPDATE collections SET name='Baja demanda' WHERE id='general';
UPDATE rules SET loan_days=14 WHERE collection_id='alta_demanda';
UPDATE rules SET loan_days=30 WHERE collection_id='general';
UPDATE metadata SET value='3' WHERE key='schema_version';
