//! Syntactically broken — adapter must not crash, error_count > 0.

pub struct Valid {
    pub field: i32,
}

pub fn valid_fn() -> i32 { 0 }

// Missing closing brace deliberately:
pub struct Broken {
    pub x: i32,
    pub y: i32,
// (no closing brace)

pub fn after_broken() -> i32 {
    1
}
