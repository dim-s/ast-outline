//! Empty- and minimal-shape edge cases.

// File starts with only inner doc + comments + uses + a single fn.

use std::io;
extern crate std;

// A block_comment that is NOT a doc.
/* not a doc comment */
pub fn lonely() {}

// Tuple-struct with only a single anonymous field.
pub struct OneTuple(pub i32);

// Empty struct (unit form).
pub struct Empty;

// Empty trait.
pub trait Marker {}

// Empty impl block (legal Rust — no methods, just claims the marker).
impl Marker for Empty {}

// Const with complex expression.
pub const COMPUTED: u32 = 1 + 2 * 3;

// Nested generic in alias.
pub type Result2<T> = Result<T, std::io::Error>;
