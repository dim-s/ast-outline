//! FFI declarations for the C math library.

use std::os::raw::c_int;

extern "C" {
    /// Computes the absolute value.
    pub fn abs(x: c_int) -> c_int;

    pub fn rand() -> c_int;

    /// Externally provided sentinel value.
    pub static MAX_VALUE: c_int;
}

extern "Rust" {
    fn rust_external_helper() -> u32;
}

#[no_mangle]
pub extern "C" fn export_to_c(x: c_int) -> c_int {
    x * 2
}
