//! Crate-level inner doc — should not attach to any item below.

// Plain non-doc comment that should NOT become docs.
pub fn no_docs() {}

/// Single-line outer doc.
pub fn single_doc() {}

/// First doc line.
/// Second doc line.
/// Third doc line.
pub fn multiline_doc() {}

/** Block doc on a single line. */
pub fn block_single() {}

/**
 * Multi-line block doc
 * with leading stars.
 */
pub fn block_multi() {}

/// Doc that has a blank line gap below — should NOT attach.

pub fn after_gap() {}

/// Outer doc on a struct.
#[derive(Debug)]
#[repr(C)]
/// Doc between attribute_items — also collected.
pub struct InterleavedDocAttrs {
    pub x: i32,
}

#[derive(Clone)]
/// Doc AFTER attribute (also a real Rust idiom).
pub fn doc_after_attr() {}

#[allow(dead_code)]
fn just_an_attr() {}
