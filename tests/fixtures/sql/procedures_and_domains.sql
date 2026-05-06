-- Constructs the tree-sitter-sql grammar can't parse natively.
-- The adapter recovers them via a regex fallback after the AST walk.
-- Comment red herring: CREATE PROCEDURE fake_in_comment() should NOT match.

/* Block-comment red herring: CREATE DOMAIN fake_in_block AS INT */

CREATE PROCEDURE log_event(msg TEXT) AS $$
BEGIN
  INSERT INTO logs(message) VALUES (msg);
  -- Body red herring: CREATE PROCEDURE inner_fake() also should NOT match
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE PROCEDURE process_batch(batch_id BIGINT, dry_run BOOLEAN DEFAULT false)
LANGUAGE plpgsql AS $$
BEGIN
  -- work
END;
$$;

CREATE PROCEDURE no_args_proc() LANGUAGE plpgsql AS $$ BEGIN END; $$;

CREATE DOMAIN positive_int AS INTEGER CHECK (VALUE > 0);
CREATE DOMAIN email_address AS TEXT CHECK (VALUE ~ '^[^@]+@[^@]+$');
CREATE DOMAIN postal_code AS VARCHAR(10);

LOAD 'auto_explain';
LOAD 'pg_stat_statements';

IMPORT FOREIGN SCHEMA remote_schema FROM SERVER fdw_server INTO local_schema;
IMPORT FOREIGN SCHEMA "Production" LIMIT TO (users, orders) FROM SERVER prod_link INTO mirror;

-- A regular CREATE TABLE here to verify mixed AST + regex output stays in source order.
CREATE TABLE log_archive (id BIGINT PRIMARY KEY, ts TIMESTAMP);
