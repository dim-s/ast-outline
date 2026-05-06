CREATE VIEW active_users AS
  SELECT * FROM users WHERE status <> 'cancelled';

CREATE VIEW high_value_orders AS
  SELECT id, user_id, total_cents FROM orders WHERE total_cents > 10000;

CREATE MATERIALIZED VIEW monthly_revenue AS
  SELECT date_trunc('month', placed_at) AS month, sum(total_cents) AS revenue
  FROM orders
  WHERE status = 'paid'
  GROUP BY 1;
