-- Pure scalar function — language SQL, no body to drill into.
CREATE FUNCTION add(a INTEGER, b INTEGER) RETURNS INTEGER AS $$
  SELECT a + b;
$$ LANGUAGE sql;

/* Returns the lifetime points balance for a user.
   Returns 0 if the user has no ledger entries. */
CREATE FUNCTION user_points(uid BIGINT) RETURNS BIGINT AS $$
BEGIN
  RETURN COALESCE((SELECT sum(delta) FROM points_ledger WHERE user_id = uid), 0);
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();
