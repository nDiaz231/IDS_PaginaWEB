CREATE TABLE student_profiles (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
 rut TEXT NOT NULL UNIQUE CHECK(length(rut) BETWEEN 9 AND 10),
 admission_year INTEGER NOT NULL CHECK(admission_year BETWEEN 1900 AND 2100),
 career TEXT NOT NULL CHECK(length(career) BETWEEN 3 AND 120),
 created_at TEXT NOT NULL,
 reviewed_at TEXT,
 reviewed_by INTEGER REFERENCES users(id),
 CHECK((reviewed_at IS NULL) = (reviewed_by IS NULL))
);
CREATE TABLE registration_attempts (
 id INTEGER PRIMARY KEY,
 client_key TEXT NOT NULL,
 attempted_at TEXT NOT NULL
);
CREATE INDEX registration_by_client ON registration_attempts(client_key,attempted_at);
CREATE INDEX registration_by_time ON registration_attempts(attempted_at);
UPDATE metadata SET value='5' WHERE key='schema_version';
