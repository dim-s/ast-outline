-- Modern PostgreSQL features the upstream grammar errors on but the
-- adapter recovers via regex fallback: declarative partitioning and
-- function modifier orderings (SECURITY DEFINER, etc).

-- Parent partitioned table parses cleanly; columns extract.
CREATE TABLE events (
  id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  payload JSONB
) PARTITION BY RANGE (ts);

-- Partition children — these parse as ERROR without the fallback.
CREATE TABLE events_2024 PARTITION OF events FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE events_2025 PARTITION OF events FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE events_default PARTITION OF events DEFAULT;

-- A regular function (parsed by AST).
CREATE FUNCTION add(a INT, b INT) RETURNS INT LANGUAGE sql AS $$ SELECT a + b $$;

-- Functions with SECURITY DEFINER — the AST errors, regex fallback
-- recovers. Both modifier orderings (before vs after LANGUAGE) work.
CREATE FUNCTION admin_op() RETURNS void
SECURITY DEFINER LANGUAGE plpgsql AS $$ BEGIN END; $$;

CREATE OR REPLACE FUNCTION trusted_op(x INT) RETURNS INT
LANGUAGE sql SECURITY DEFINER AS $$ SELECT x $$;
