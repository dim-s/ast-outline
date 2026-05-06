-- Flyway-style migration: V0017__add_points_index.sql

ALTER TABLE points_ledger ADD COLUMN expires_at TIMESTAMP;

CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_ledger_user_created ON points_ledger(user_id, created_at);

CREATE SEQUENCE order_id_seq START 100000 INCREMENT 1;
