//! Shared ownership of versioned payloads and checked, fixed selectors.
//!
//! No Python objects or callbacks live in the core. IDs are append-only
//! positions; references never point into a vector that can reallocate.

mod affine;
mod coordinates;
mod domain;
mod membership;
mod selector;
mod sparse;
mod storage;

pub use affine::{Affine, AlgebraError, Number, Row, Term};
pub use coordinates::Coordinates;
pub use membership::Membership;
pub use selector::Selector;
pub use sparse::Sparse;
pub use storage::{Owner, Payload, Snapshot, StorageError};
