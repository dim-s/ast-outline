//! Trait hierarchy for testing `implements` (direct + transitive).

/// Top of the hierarchy.
pub trait Animal {
    fn name(&self) -> String;
}

/// Refines `Animal` with locomotion.
pub trait Quadruped: Animal {
    fn legs(&self) -> u32 {
        4
    }
}

/// Refines `Quadruped` further with social behaviour.
pub trait PackAnimal: Quadruped {
    fn pack_size(&self) -> u32;
}

pub struct Dog {
    pub breed: String,
}

pub struct Wolf {
    pub pack: u32,
}

pub struct Cat;

impl Animal for Dog {
    fn name(&self) -> String {
        format!("dog ({})", self.breed)
    }
}

impl Quadruped for Dog {}

impl Animal for Wolf {
    fn name(&self) -> String {
        "wolf".into()
    }
}

impl Quadruped for Wolf {}

impl PackAnimal for Wolf {
    fn pack_size(&self) -> u32 {
        self.pack
    }
}

impl Animal for Cat {
    fn name(&self) -> String {
        "cat".into()
    }
}

impl Quadruped for Cat {}
