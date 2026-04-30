//! Module-level inner doc — should not attach to any specific item.

use std::collections::HashMap;

/// Represents a registered user account.
///
/// Carries the public name visible to others plus the (private) raw
/// id used for storage indexing.
#[derive(Debug, Clone)]
pub struct User {
    pub name: String,
    pub email: String,
    id: u64,
}

/// Trait describing anything that can be addressed by a unique id.
pub trait HasId {
    /// Numeric identifier — must be stable for the lifetime of the value.
    fn id(&self) -> u64;
}

/// Service that owns a registry of users keyed by id.
pub struct UserService {
    users: HashMap<u64, User>,
}

impl User {
    /// Constructor — assigns a fresh id at creation time.
    pub fn new(name: String, email: String, id: u64) -> Self {
        User { name, email, id }
    }

    /// Read-only accessor for the raw id.
    pub fn raw_id(&self) -> u64 {
        self.id
    }

    fn internal_check(&self) -> bool {
        !self.name.is_empty()
    }
}

impl HasId for User {
    fn id(&self) -> u64 {
        self.id
    }
}

impl UserService {
    pub fn new() -> Self {
        UserService {
            users: HashMap::new(),
        }
    }

    pub fn register(&mut self, user: User) {
        self.users.insert(user.id, user);
    }

    pub fn lookup(&self, id: u64) -> Option<&User> {
        self.users.get(&id)
    }
}

/// Free top-level helper.
pub fn format_user(user: &User) -> String {
    format!("{} <{}>", user.name, user.email)
}

pub const MAX_USERS: u32 = 10_000;
static SERVICE_NAME: &str = "user-service";
