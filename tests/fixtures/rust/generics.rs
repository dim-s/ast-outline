//! Generics, lifetimes, where clauses, associated types.

use std::fmt::Debug;

pub struct Wrapper<T: Clone + Send + Sync> {
    pub inner: T,
}

pub struct Pair<A, B> {
    pub first: A,
    pub second: B,
}

pub fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

pub fn complex<'a, 'b: 'a, T, U>(x: &'a T, y: &'b U) -> (&'a T, &'b U)
where
    T: Debug + Clone,
    U: Debug + Send + 'static,
{
    (x, y)
}

pub trait Container {
    type Item;
    type Iter<'a>: Iterator<Item = &'a Self::Item>
    where
        Self: 'a;

    fn iter(&self) -> Self::Iter<'_>;
    fn len(&self) -> usize;
}

pub struct VecContainer<T> {
    items: Vec<T>,
}

impl<T> Container for VecContainer<T> {
    type Item = T;
    type Iter<'a> = std::slice::Iter<'a, T> where T: 'a;

    fn iter(&self) -> Self::Iter<'_> {
        self.items.iter()
    }

    fn len(&self) -> usize {
        self.items.len()
    }
}

pub fn process<T, F>(item: T, f: F) -> T
where
    F: Fn(T) -> T,
{
    f(item)
}
