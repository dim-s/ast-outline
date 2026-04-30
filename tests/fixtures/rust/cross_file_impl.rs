//! Methods implemented on types declared elsewhere — orphan-spill behaviour.

use crate::other_crate::ExternalType;

// `ExternalType` is not declared in this file. Its impl block's items
// should still surface; per the per-file outline convention, they spill
// at top level of THIS file (rather than being silently dropped).
impl ExternalType {
    pub fn extension_method(&self) -> u32 {
        42
    }

    pub fn another_extension(&self) -> bool {
        true
    }
}

pub trait LocalTrait {
    fn marker(&self);
}

// Trait impl on a foreign type — same orphan-spill rule.
impl LocalTrait for ExternalType {
    fn marker(&self) {}
}

// And a local-on-local impl for sanity.
pub struct LocalType;

impl LocalType {
    pub fn local_method(&self) {}
}
