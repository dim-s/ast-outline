//! Enums covering every variant shape Rust offers.

/// Plain unit-variant enum (C-style).
pub enum Direction {
    North,
    South,
    East,
    West,
}

/// Mixed variants — unit, tuple, struct, generic.
pub enum Event<T> {
    /// Boring nothing-happened ping.
    Idle,
    /// Started a job; carries the job id.
    Started(u64),
    /// Job ran for a while; carries multiple positional fields.
    Progressing(u64, f32),
    /// Finished — named fields make the payload self-describing.
    Completed { id: u64, duration_ms: u64 },
    /// Carries arbitrary user-typed payload.
    Custom(T),
}

/// Enum variants can carry attributes and discriminants too.
#[repr(u8)]
pub enum Code {
    Ok = 0,
    NotFound = 1,
    #[deprecated]
    Internal = 99,
}
