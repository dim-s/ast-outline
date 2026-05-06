-- Application schema for the loyalty programme.
-- Mirrors a typical pg_dump artefact — schemas, types, tables, FKs.

CREATE SCHEMA loyalty;

-- Status of an order in the fulfilment pipeline.
CREATE TYPE order_status AS ENUM ('pending', 'paid', 'shipped', 'cancelled');

CREATE TYPE address AS (
  street TEXT,
  city TEXT,
  zip TEXT
);

/* Users of the loyalty programme. The `email` column is the
   external identity used in JWTs; treat it as immutable. */
CREATE TABLE users (
  id BIGINT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT,
  status order_status NOT NULL DEFAULT 'pending',
  shipping_address address,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP
);

-- Reward points earned per user, aggregated nightly.
CREATE TABLE points_ledger (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  delta INTEGER NOT NULL CHECK (delta <> 0),
  reason TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  total_cents INTEGER NOT NULL,
  status order_status NOT NULL DEFAULT 'pending',
  placed_at TIMESTAMP NOT NULL DEFAULT now()
);
