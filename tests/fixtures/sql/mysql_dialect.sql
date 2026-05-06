-- Realistic MySQL schema. Demonstrates that DDL extracts cleanly
-- despite MySQL-specific clauses (ENGINE=, CHARSET=, AUTO_INCREMENT,
-- inline KEY definitions) that surface as parse-error noise.

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  display_name VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  total DECIMAL(10,2) NOT NULL,
  status ENUM('pending', 'paid', 'shipped') DEFAULT 'pending',
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status, created_at DESC);

CREATE VIEW active_users AS SELECT * FROM users WHERE deleted_at IS NULL;
