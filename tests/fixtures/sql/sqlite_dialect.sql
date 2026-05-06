-- Realistic SQLite schema. AUTOINCREMENT and FTS5 virtual tables
-- are SQLite-specific; tables and columns extract cleanly.

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT,
  created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_posts_user ON posts(user_id);
CREATE INDEX idx_posts_title ON posts(title);

CREATE VIEW recent_posts AS SELECT * FROM posts ORDER BY id DESC LIMIT 50;
