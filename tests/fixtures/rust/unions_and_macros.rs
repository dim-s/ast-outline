//! Less-common but valid Rust constructs: unions and macro_rules.

/// Discriminated union — carries either an int or a float.
#[repr(C)]
pub union NumOrFloat {
    pub i: i32,
    pub f: f32,
}

/// A simple `vec!`-flavoured macro.
#[macro_export]
macro_rules! my_vec {
    () => { Vec::new() };
    ($($x:expr),*) => {
        {
            let mut v = Vec::new();
            $(v.push($x);)*
            v
        }
    };
}

/// Expression-position macro definition.
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}

pub fn use_macros() -> Vec<i32> {
    my_vec![1, 2, 3]
}
