//! Stable roots, detachable payload handles and immutable data versions.

use crate::Selector;
use std::sync::{Arc, RwLock};

/// Recoverable storage errors are translated at the Python boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StorageError {
    Index,
    Length,
    Poisoned,
    VersionOverflow,
}

/// One mutable payload handle; snapshots pin earlier immutable vectors.
#[derive(Debug)]
pub struct Payload<T> {
    state: Arc<RwLock<Version<T>>>,
}

#[derive(Debug)]
struct Version<T> {
    number: u64,
    values: Arc<Vec<T>>,
}

/// A root has stable identity even when replacement detaches its old payload.
#[derive(Debug)]
pub struct Owner<T> {
    current: RwLock<Payload<T>>,
}

/// Fixed membership and an immutable data version outlive their source owner.
#[derive(Clone, Debug)]
pub struct Snapshot<T> {
    values: Arc<Vec<T>>,
    selector: Selector,
    version: u64,
}

impl<T> Clone for Payload<T> {
    /// Share the payload lock and version without duplicating data.
    fn clone(&self) -> Self {
        Self {
            state: Arc::clone(&self.state),
        }
    }
}

impl<T: Clone> Owner<T> {
    /// Create an authoritative root from already validated Rust values.
    pub fn new(values: Vec<T>) -> Self {
        Self {
            current: RwLock::new(Payload::new(values)),
        }
    }

    /// Clone a payload handle, not its data; retained handles survive replacement.
    pub fn payload(&self) -> Result<Payload<T>, StorageError> {
        Ok(self
            .current
            .read()
            .map_err(|_| StorageError::Poisoned)?
            .clone())
    }

    /// Replace the complete payload atomically, preserving this root's identity.
    pub fn replace(&self, values: Vec<T>) -> Result<(), StorageError> {
        let replacement = Payload::new(values);
        *self.current.write().map_err(|_| StorageError::Poisoned)? = replacement;
        Ok(())
    }
}

impl<T: Clone> Payload<T> {
    /// Construct one payload; no foreign callbacks occur while holding a lock.
    pub fn new(values: Vec<T>) -> Self {
        Self {
            state: Arc::new(RwLock::new(Version {
                number: 0,
                values: Arc::new(values),
            })),
        }
    }

    /// Capture a data version and selection under one shared lock.
    pub fn snapshot(&self, selector: Selector) -> Result<Snapshot<T>, StorageError> {
        let state = self.state.read().map_err(|_| StorageError::Poisoned)?;
        selector.validate(state.values.len())?;
        Ok(Snapshot {
            values: Arc::clone(&state.values),
            selector,
            version: state.number,
        })
    }

    /// Snapshot all current members in constant space.
    pub fn all(&self) -> Result<Snapshot<T>, StorageError> {
        let state = self.state.read().map_err(|_| StorageError::Poisoned)?;
        let selector = Selector::span(0, 1, state.values.len(), state.values.len())?;
        Ok(Snapshot {
            values: Arc::clone(&state.values),
            selector,
            version: state.number,
        })
    }

    /// Validate the whole update before copy-on-write and a single version bump.
    pub fn set_many(&self, positions: &[usize], values: Vec<T>) -> Result<(), StorageError> {
        if positions.len() != values.len() {
            return Err(StorageError::Length);
        }
        let mut state = self.state.write().map_err(|_| StorageError::Poisoned)?;
        if positions.iter().any(|p| *p >= state.values.len()) {
            return Err(StorageError::Index);
        }
        if positions.is_empty() {
            return Ok(());
        }
        let next = state
            .number
            .checked_add(1)
            .ok_or(StorageError::VersionOverflow)?;
        for (position, value) in positions.iter().zip(values) {
            Arc::make_mut(&mut state.values)[*position] = value;
        }
        state.number = next;
        Ok(())
    }

    /// Append preserves all prior positions and fixed snapshot memberships.
    pub fn append(&self, values: Vec<T>) -> Result<(), StorageError> {
        if values.is_empty() {
            return Ok(());
        }
        let mut state = self.state.write().map_err(|_| StorageError::Poisoned)?;
        let next = state
            .number
            .checked_add(1)
            .ok_or(StorageError::VersionOverflow)?;
        Arc::make_mut(&mut state.values).extend(values);
        state.number = next;
        Ok(())
    }
}

impl<T: Clone> Snapshot<T> {
    /// Share the captured value version through compact nested membership.
    pub fn select(&self, positions: &Selector) -> Result<Self, StorageError> {
        Ok(Self {
            values: Arc::clone(&self.values),
            selector: self.selector.compose(positions)?,
            version: self.version,
        })
    }
    /// Compose fixed membership without copying the retained data version.
    pub fn take(&self, positions: Vec<usize>) -> Result<Self, StorageError> {
        let ids = positions
            .into_iter()
            .map(|p| self.selector.at(p))
            .collect::<Result<Vec<_>, _>>()?;
        Ok(Self {
            values: Arc::clone(&self.values),
            selector: Selector::compact(ids, self.values.len())?,
            version: self.version,
        })
    }

    /// Read an immutable version, never an address into mutable storage.
    pub fn get(&self, position: usize) -> Result<T, StorageError> {
        self.values
            .get(self.selector.at(position)?)
            .cloned()
            .ok_or(StorageError::Index)
    }

    /// Materialize only on explicit traversal/export.
    pub fn values(&self) -> Result<Vec<T>, StorageError> {
        (0..self.len()).map(|position| self.get(position)).collect()
    }

    /// A fixed selector does not grow when its original payload grows.
    pub fn len(&self) -> usize {
        self.selector.len()
    }
    /// Empty snapshots are valid.
    pub fn is_empty(&self) -> bool {
        self.selector.is_empty()
    }
    /// Version is local to the retained payload, not a global expression cache.
    pub fn version(&self) -> u64 {
        self.version
    }
    /// Reserved vector bytes exclude Arc/lock/selector bookkeeping.
    pub fn reserved_bytes(&self) -> usize {
        self.values.capacity() * std::mem::size_of::<T>()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    /// Numeric product snapshots share versions and detach safely on owner writes.
    fn product_snapshot_versions_and_nested_membership() {
        let payload = Payload::new((0..12).collect::<Vec<_>>());
        let axes = vec![
            Selector::span(3, -1, 4, 4).unwrap(),
            Selector::span(0, 2, 2, 3).unwrap(),
        ];
        let selected = payload
            .snapshot(Selector::product(axes, vec![4, 3]).unwrap())
            .unwrap();
        let local = Selector::product(
            vec![
                Selector::span(1, 1, 2, 4).unwrap(),
                Selector::span(1, 1, 1, 2).unwrap(),
            ],
            vec![4, 2],
        )
        .unwrap();
        let nested = selected.select(&local).unwrap();
        payload.set_many(&[5, 8], vec![50, 80]).unwrap();
        assert_eq!(nested.values().unwrap(), [8, 5]);
        assert_eq!(nested.version(), 0);
        drop(payload);
        drop(selected);
        assert_eq!(nested.values().unwrap(), [8, 5]);
    }

    #[test]
    /// Root replacement and snapshot release have independent lifetimes.
    fn replacement_and_snapshot_lifetimes() {
        let root = Owner::new(vec![1, 2, 3]);
        let payload = root.payload().unwrap();
        let snapshot = payload.all().unwrap();
        let weak = Arc::downgrade(&snapshot.values);
        root.replace(vec![4, 5]).unwrap();
        payload.set_many(&[0], vec![9]).unwrap();
        assert_eq!(snapshot.values().unwrap(), [1, 2, 3]);
        assert_eq!(
            root.payload().unwrap().all().unwrap().values().unwrap(),
            [4, 5]
        );
        drop(root);
        drop(payload);
        assert!(weak.upgrade().is_some());
        drop(snapshot);
        assert!(weak.upgrade().is_none());
    }

    #[test]
    /// Failed validation changes neither data nor version; append keeps IDs.
    fn failed_update_is_atomic_and_append_preserves_ids() {
        let payload = Payload::new(vec![2, 3]);
        assert_eq!(
            payload.set_many(&[0, 2], vec![8, 9]),
            Err(StorageError::Index)
        );
        assert_eq!(
            payload.set_many(&[0], vec![8, 9]),
            Err(StorageError::Length)
        );
        let old = payload.all().unwrap();
        assert_eq!(old.version(), 0);
        payload.append(vec![4]).unwrap();
        assert_eq!(old.values().unwrap(), [2, 3]);
        assert_eq!(payload.all().unwrap().values().unwrap(), [2, 3, 4]);
    }

    #[test]
    /// Readers may see either whole batch, never a partially applied batch.
    fn concurrent_batches_are_never_observed_half_written() {
        let payload = Payload::new(vec![0, 0]);
        let writer = payload.clone();
        let thread = std::thread::spawn(move || {
            for value in 0..1000 {
                writer.set_many(&[0, 1], vec![value, value]).unwrap();
            }
        });
        for _ in 0..1000 {
            let values = payload.all().unwrap().values().unwrap();
            assert_eq!(values[0], values[1]);
        }
        thread.join().unwrap();
    }

    #[test]
    /// Selection preserves order and rejects invalid positions.
    fn selectors_preserve_order_duplicates_and_boundary_errors() {
        let payload = Payload::new(vec![10, 20, 30]);
        let reversed = payload
            .snapshot(Selector::span(2, -1, 3, 3).unwrap())
            .unwrap();
        assert_eq!(reversed.values().unwrap(), [30, 20, 10]);
        let repeated = payload
            .snapshot(Selector::indices(vec![2, 0, 2], 3).unwrap())
            .unwrap();
        assert_eq!(repeated.values().unwrap(), [30, 10, 30]);
        assert!(Selector::span(0, -1, 2, 3).is_err());
        assert!(Selector::span(0, 0, 0, 0).is_err());
        assert!(Selector::indices(vec![3], 3).is_err());
        assert!(reversed.get(3).is_err());
    }

    #[test]
    /// Empty and nested snapshots validate independently of source lifetimes.
    fn empty_nested_and_extreme_selectors() {
        let payload = Payload::new(vec![10, 20, 30]);
        let snapshot = payload.all().unwrap();
        assert_eq!(
            snapshot.take(vec![2, 0, 2]).unwrap().values().unwrap(),
            [30, 10, 30]
        );
        assert!(snapshot.take(vec![3]).is_err());
        let empty = snapshot.take(vec![]).unwrap();
        assert!(empty.is_empty());
        assert!(empty.get(0).is_err());
        assert!(empty.values().unwrap().is_empty());
        assert!(Selector::span(usize::MAX, isize::MAX, usize::MAX, 3).is_err());
        assert!(payload
            .snapshot(Selector::span(0, 1, 4, 4).unwrap())
            .is_err());
        assert!(payload
            .snapshot(Selector::indices(vec![3], 4).unwrap())
            .is_err());
        assert!(Selector::span(usize::MAX, 1, 0, 0).unwrap().is_empty());
        assert!(snapshot.reserved_bytes() >= 3 * std::mem::size_of::<i32>());
    }

    #[test]
    /// Exhausted versions reject mutation without changing values.
    fn version_exhaustion_is_atomic() {
        let payload = Payload::new(vec![1]);
        payload.state.write().unwrap().number = u64::MAX;
        assert_eq!(
            payload.set_many(&[0], vec![2]),
            Err(StorageError::VersionOverflow)
        );
        assert_eq!(payload.append(vec![2]), Err(StorageError::VersionOverflow));
        payload.set_many(&[], vec![]).unwrap();
        payload.append(vec![]).unwrap();
        assert_eq!(payload.all().unwrap().values().unwrap(), [1]);
    }

    #[test]
    /// A panicking writer poisons storage and subsequent access reports it.
    fn poisoned_locks_report_errors() {
        let payload = Payload::new(vec![1]);
        let writer = payload.clone();
        assert!(std::thread::spawn(move || {
            let _guard = writer.state.write().unwrap();
            panic!("intentional poison test");
        })
        .join()
        .is_err());
        assert_eq!(payload.all().unwrap_err(), StorageError::Poisoned);
        assert_eq!(payload.set_many(&[0], vec![2]), Err(StorageError::Poisoned));
        assert_eq!(payload.append(vec![2]), Err(StorageError::Poisoned));
    }
}
