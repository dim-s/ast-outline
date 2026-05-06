CREATE TABLE "User Profile" (
  "Email Address" TEXT NOT NULL,
  "Display Name" TEXT
);

CREATE TABLE analytics.events (
  id BIGINT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  payload TEXT
);
