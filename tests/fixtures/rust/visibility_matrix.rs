//! Visibility classifier coverage.

pub fn fully_public() {}
pub(crate) fn crate_only() {}
pub(super) fn super_only() {}
pub(self) fn self_only() {}
pub(in crate::root) fn in_path() {}
fn private_default() {}

pub struct PubStruct;
pub(crate) struct CrateStruct;
struct PrivateStruct;

pub const PUB_CONST: u32 = 1;
pub(crate) const CRATE_CONST: u32 = 2;
const PRIVATE_CONST: u32 = 3;

pub static PUB_STATIC: u32 = 10;
static PRIVATE_STATIC: u32 = 20;
