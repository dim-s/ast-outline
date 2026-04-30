//! Module-level inner doc.

pub mod outer {
    //! Inner doc inside the module.

    pub struct Public;
    struct PrivateInModule;
    pub(crate) struct CrateOnly;
    pub(super) struct SuperOnly;

    pub fn exported() {}
    fn internal() {}
    pub(crate) fn crate_helper() {}

    pub mod nested {
        pub fn deep_call() {}

        pub mod even_deeper {
            pub struct DeepStruct;
        }
    }
}

/// External-file module reference (no body).
pub mod external_a;

mod external_b;

pub(crate) mod restricted_external;
