//! Append-only coordinate tables with stable member IDs and shared selectors.

use crate::domain::Domain;
use crate::{Selector, StorageError};
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, RwLock};

/// Python interns axis objects before entry; only integer tokens enter the core.
#[derive(Debug)]
struct Table<T> {
    // Sparse coordinates follow the compact product prefix, if present.
    positions: HashMap<Arc<[usize]>, usize>,
    keys: Vec<Arc<[usize]>>,
    records: Vec<T>,
    domain: Option<Domain>,
}

impl<T> Table<T> {
    /// Keep product membership compact even after irregular rows are appended.
    fn lookup(&self, key: &[usize]) -> Result<usize, StorageError> {
        self.domain
            .as_ref()
            .and_then(|domain| domain.lookup(key))
            .or_else(|| self.positions.get(key).copied())
            .ok_or(StorageError::Index)
    }

    /// Decode a product row on demand or copy a sparse-tail coordinate.
    fn key(&self, id: usize) -> Result<Vec<usize>, StorageError> {
        let prefix = self.domain.as_ref().map_or(0, Domain::len);
        if id < prefix {
            return self
                .domain
                .as_ref()
                .and_then(|domain| domain.key(id))
                .ok_or(StorageError::Index);
        }
        self.keys
            .get(id - prefix)
            .map(|key| key.to_vec())
            .ok_or(StorageError::Index)
    }
}

/// One authoritative coordinate/record store, shared by fixed-membership views.
#[derive(Clone, Debug)]
pub struct Coordinates<T> {
    table: Arc<RwLock<Table<T>>>,
    selector: Option<Selector>,
}

impl<T: Clone> Coordinates<T> {
    /// Validate uniqueness and lengths before publishing a new root.
    pub fn new(keys: Vec<Vec<usize>>, records: Vec<T>) -> Result<Self, StorageError> {
        if keys.len() != records.len() {
            return Err(StorageError::Length);
        }
        if let Some(domain) = Domain::infer(&keys) {
            return Self::from_domain(domain, records);
        }
        let owner = Self {
            table: Arc::new(RwLock::new(Table {
                positions: HashMap::new(),
                keys: Vec::new(),
                records: Vec::new(),
                domain: None,
            })),
            selector: None,
        };
        owner.append(keys, records)?;
        Ok(owner)
    }

    /// Construct directly from ordered unique axes, without expanded key rows.
    pub fn cartesian(axes: Vec<Vec<usize>>, records: Vec<T>) -> Result<Self, StorageError> {
        Self::from_domain(Domain::new(axes)?, records)
    }

    /// Validate record cardinality before publishing compact coordinate storage.
    fn from_domain(domain: Domain, records: Vec<T>) -> Result<Self, StorageError> {
        if domain.len() != records.len() {
            return Err(StorageError::Length);
        }
        Ok(Self {
            table: Arc::new(RwLock::new(Table {
                positions: HashMap::new(),
                keys: Vec::new(),
                records,
                domain: Some(domain),
            })),
            selector: None,
        })
    }

    /// Root membership grows; a selection's membership remains fixed.
    pub fn len(&self) -> Result<usize, StorageError> {
        match &self.selector {
            Some(selector) => Ok(selector.len()),
            None => Ok(self
                .table
                .read()
                .map_err(|_| StorageError::Poisoned)?
                .records
                .len()),
        }
    }

    /// Empty roots and selectors are valid.
    pub fn is_empty(&self) -> Result<bool, StorageError> {
        Ok(self.len()? == 0)
    }

    /// Resolve a local position to its stable owner ID.
    pub fn id(&self, position: usize) -> Result<usize, StorageError> {
        match &self.selector {
            Some(selector) => selector.at(position),
            None if position < self.len()? => Ok(position),
            None => Err(StorageError::Index),
        }
    }

    /// Return a detached token coordinate; no pointers into growable vectors escape.
    pub fn key(&self, position: usize) -> Result<Vec<usize>, StorageError> {
        let id = self.id(position)?;
        self.table
            .read()
            .map_err(|_| StorageError::Poisoned)?
            .key(id)
    }

    /// Lookup respects view membership and coordinate order.
    pub fn lookup(&self, key: &[usize]) -> Result<usize, StorageError> {
        let table = self.table.read().map_err(|_| StorageError::Poisoned)?;
        let id = table.lookup(key)?;
        match &self.selector {
            Some(selector) => selector.position(id).ok_or(StorageError::Index),
            None => Ok(id),
        }
    }

    /// Resolve a complete selection under one read lock, without foreign callbacks.
    pub fn lookup_many(&self, keys: &[Vec<usize>]) -> Result<Vec<usize>, StorageError> {
        let table = self.table.read().map_err(|_| StorageError::Poisoned)?;
        keys.iter()
            .map(|key| {
                let id = table.lookup(key)?;
                match &self.selector {
                    Some(selector) => selector.position(id).ok_or(StorageError::Index),
                    None => Ok(id),
                }
            })
            .collect()
    }

    /// Copy one small record while holding only a shared lock.
    pub fn get(&self, position: usize) -> Result<T, StorageError> {
        let id = self.id(position)?;
        Ok(self
            .table
            .read()
            .map_err(|_| StorageError::Poisoned)?
            .records[id]
            .clone())
    }

    /// Export records from one coherent view under a single shared lock.
    pub fn values(&self) -> Result<Vec<T>, StorageError> {
        let table = self.table.read().map_err(|_| StorageError::Poisoned)?;
        match &self.selector {
            None => Ok(table.records.clone()),
            Some(selector) => (0..selector.len())
                .map(|position| Ok(table.records[selector.at(position)?].clone()))
                .collect(),
        }
    }

    /// Read selected owner IDs and records together under one lock.
    pub fn entries(&self) -> Result<Vec<(usize, T)>, StorageError> {
        let table = self.table.read().map_err(|_| StorageError::Poisoned)?;
        match &self.selector {
            None => Ok(table.records.iter().cloned().enumerate().collect()),
            Some(selector) => (0..selector.len())
                .map(|position| {
                    let id = selector.at(position)?;
                    Ok((id, table.records[id].clone()))
                })
                .collect(),
        }
    }

    /// Update a record without changing coordinates or member identity.
    pub fn set(&self, position: usize, record: T) -> Result<(), StorageError> {
        let id = self.id(position)?;
        self.table
            .write()
            .map_err(|_| StorageError::Poisoned)?
            .records[id] = record;
        Ok(())
    }

    /// Compose local IDs and compact arithmetic progressions in constant space.
    pub fn take(&self, positions: Vec<usize>) -> Result<Self, StorageError> {
        let bound = self
            .table
            .read()
            .map_err(|_| StorageError::Poisoned)?
            .records
            .len();
        let ids = positions
            .into_iter()
            .map(|position| match &self.selector {
                Some(selector) => selector.at(position),
                None if position < bound => Ok(position),
                None => Err(StorageError::Index),
            })
            .collect::<Result<Vec<_>, _>>()?;
        Ok(Self {
            table: self.table.clone(),
            selector: Some(Selector::compact(ids, bound)?),
        })
    }

    /// Freeze full membership without enumerating coordinates or records.
    pub fn freeze(&self) -> Result<Self, StorageError> {
        let selector = match &self.selector {
            Some(selector) => selector.clone(),
            None => Selector::span(0, 1, self.len()?, self.len()?)?,
        };
        Ok(Self {
            table: self.table.clone(),
            selector: Some(selector),
        })
    }

    /// Select axis products without Python coordinate expansion or scalar records.
    pub fn product(&self, axes: Vec<Vec<usize>>) -> Result<(Self, Selector), StorageError> {
        self.product_for(axes, false)
    }

    /// Retain first-member or last-expression duplicate lookup explicitly.
    pub fn product_for(
        &self,
        axes: Vec<Vec<usize>>,
        last: bool,
    ) -> Result<(Self, Selector), StorageError> {
        let table = self.table.read().map_err(|_| StorageError::Poisoned)?;
        if axes.iter().any(Vec::is_empty) {
            let empty = Selector::span(0, 1, 0, table.records.len())?;
            return Ok((
                Self {
                    table: self.table.clone(),
                    selector: Some(empty.clone()),
                },
                empty,
            ));
        }
        let selectors = match &table.domain {
            Some(domain) if domain.len() == table.records.len() => {
                domain.select(&axes, self.selector.as_ref(), last)?
            }
            _ => None,
        };
        let (owner, local) = match selectors {
            Some(pair) => pair,
            None => self.resolve_product(&axes, &table, last)?,
        };
        Ok((
            Self {
                table: self.table.clone(),
                selector: Some(owner),
            },
            local,
        ))
    }

    /// Irregular domains enumerate only in Rust with the caller's duplicate policy.
    fn resolve_product(
        &self,
        axes: &[Vec<usize>],
        table: &Table<T>,
        last: bool,
    ) -> Result<(Selector, Selector), StorageError> {
        let lengths: Vec<_> = axes.iter().map(Vec::len).collect();
        let size = lengths
            .iter()
            .try_fold(1usize, |n, size| n.checked_mul(*size))
            .ok_or(StorageError::Index)?;
        let mut owner = Vec::with_capacity(size);
        let mut local = Vec::with_capacity(size);
        let mut key = vec![0; axes.len()];
        for position in 0..size {
            let mut rest = position;
            for (n, axis) in axes.iter().enumerate().rev() {
                key[n] = axis[rest % axis.len()];
                rest /= axis.len();
            }
            let id = table.lookup(&key)?;
            owner.push(id);
            local.push(match &self.selector {
                Some(selector) => selector.position_for(id, last).ok_or(StorageError::Index)?,
                None => id,
            });
        }
        let bound = self
            .selector
            .as_ref()
            .map_or(table.records.len(), Selector::len);
        Ok((
            Selector::compact(owner, table.records.len())?,
            Selector::compact(local, bound)?,
        ))
    }

    /// Validate a complete append before changing any table or record vector.
    pub fn append(&self, keys: Vec<Vec<usize>>, records: Vec<T>) -> Result<(), StorageError> {
        if self.selector.is_some() || keys.len() != records.len() {
            return Err(StorageError::Length);
        }
        let keys: Vec<Arc<[usize]>> = keys.into_iter().map(Arc::from).collect();
        let mut table = self.table.write().map_err(|_| StorageError::Poisoned)?;
        let mut seen = HashSet::new();
        for key in &keys {
            if table.lookup(key).is_ok() || !seen.insert(key) {
                return Err(StorageError::Index);
            }
        }
        let prefix = table.domain.as_ref().map_or(0, Domain::len);
        for key in keys {
            let id = prefix + table.keys.len();
            table.positions.insert(key.clone(), id);
            table.keys.push(key);
        }
        table.records.extend(records);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    /// Inferred and direct products own axes only, regardless of row count.
    fn compact_roots_round_trip_coordinates() {
        let keys: Vec<_> = [8, 3, 4]
            .into_iter()
            .flat_map(|i| [7, 2].into_iter().map(move |j| vec![i, j]))
            .collect();
        let inferred = Coordinates::new(keys.clone(), (0..6).collect()).unwrap();
        let direct =
            Coordinates::cartesian(vec![vec![8, 3, 4], vec![7, 2]], (0..6).collect()).unwrap();
        for root in [inferred, direct] {
            assert!(root.table.read().unwrap().keys.is_empty());
            assert!(root.table.read().unwrap().positions.is_empty());
            for (n, key) in keys.iter().enumerate() {
                assert_eq!(root.key(n).unwrap(), *key);
                assert_eq!(root.lookup(key).unwrap(), n);
            }
            assert!(root.lookup(&[8]).is_err());
            assert!(root.lookup(&[8, 7, 0]).is_err());
            assert!(root.lookup(&[9, 7]).is_err());
            assert!(root.key(6).is_err());
        }
    }

    #[test]
    /// Growth adds only sparse rows, retaining compact prefixes and stable views.
    fn compact_prefix_survives_growth_and_rejected_batches() {
        let root = Coordinates::cartesian(vec![vec![2, 1], vec![4, 5]], vec![0, 1, 2, 3]).unwrap();
        let fixed = root.freeze().unwrap();
        let reverse = root.take(vec![3, 0, 3]).unwrap();
        assert!(root
            .append(vec![vec![9, 4], vec![2, 4]], vec![4, 5])
            .is_err());
        assert_eq!(root.len().unwrap(), 4);
        root.append(vec![vec![9, 4], vec![9, 5]], vec![4, 5])
            .unwrap();
        assert_eq!(root.table.read().unwrap().keys.len(), 2);
        assert!(root
            .append(vec![vec![7, 4], vec![9, 5]], vec![6, 7])
            .is_err());
        assert!(root.lookup(&[7, 4]).is_err());
        assert_eq!(fixed.len().unwrap(), 4);
        assert!(fixed.lookup(&[9, 5]).is_err());
        let (mixed, _) = root.product(vec![vec![9, 1], vec![5, 4]]).unwrap();
        assert_eq!(mixed.values().unwrap(), [5, 4, 3, 2]);
        reverse.set(0, 33).unwrap();
        assert_eq!(fixed.get(3).unwrap(), 33);
        assert_eq!(root.lookup_many(&[vec![9, 4], vec![2, 4]]).unwrap(), [4, 0]);
        assert_eq!(root.key(5).unwrap(), [9, 5]);
        assert!(reverse.product(vec![vec![9], vec![4]]).is_err());
    }

    #[test]
    /// Empty axes and the rank-zero singleton have distinct cardinalities.
    fn cartesian_empty_and_scalar_domains() {
        let empty = Coordinates::<usize>::cartesian(vec![vec![3], vec![]], vec![]).unwrap();
        assert!(empty.is_empty().unwrap());
        assert!(empty.key(0).is_err());
        assert!(empty.lookup(&[3, 1]).is_err());
        empty.append(vec![vec![3, 1]], vec![7]).unwrap();
        assert_eq!(empty.key(0).unwrap(), [3, 1]);
        assert_eq!(empty.lookup(&[3, 1]).unwrap(), 0);
        let scalar = Coordinates::cartesian(vec![], vec![7]).unwrap();
        assert_eq!(scalar.key(0).unwrap(), Vec::<usize>::new());
        assert_eq!(scalar.lookup(&[]).unwrap(), 0);
        assert_eq!(scalar.product(vec![]).unwrap().0.values().unwrap(), [7]);
        assert!(scalar.append(vec![vec![]], vec![8]).is_err());
        scalar.append(vec![vec![9]], vec![8]).unwrap();
        assert_eq!(scalar.key(1).unwrap(), [9]);
    }

    #[test]
    /// Invalid axes and overflowing shapes fail before publishing any owner.
    fn cartesian_rejects_duplicate_axes_lengths_and_overflow() {
        assert!(Coordinates::cartesian(vec![vec![1, 1]], vec![1, 2]).is_err());
        assert!(Coordinates::cartesian(vec![vec![1, 2]], vec![1]).is_err());
        assert!(
            Coordinates::<usize>::cartesian(vec![vec![0, 1]; usize::BITS as usize], vec![])
                .is_err()
        );
        let mut axes = vec![vec![0, 1]; usize::BITS as usize];
        axes.push(vec![]);
        let empty = Coordinates::<usize>::cartesian(axes, vec![]).unwrap();
        assert!(empty.lookup(&vec![1; usize::BITS as usize + 1]).is_err());
    }

    #[test]
    /// Irregular row order and mixed ranks keep sparse insertion-order semantics.
    fn irregular_roots_do_not_infer_false_products() {
        let keys = vec![vec![0, 3], vec![1, 4], vec![0, 4], vec![1, 3]];
        let root = Coordinates::new(keys.clone(), (0..4).collect()).unwrap();
        assert!(root.table.read().unwrap().domain.is_none());
        for (n, key) in keys.iter().enumerate() {
            assert_eq!(root.key(n).unwrap(), *key);
            assert_eq!(root.lookup(key).unwrap(), n);
        }
        let mixed = Coordinates::new(vec![vec![], vec![0]], vec![1, 2]).unwrap();
        assert!(mixed.table.read().unwrap().domain.is_none());
        assert_eq!(mixed.lookup(&[]).unwrap(), 0);
        assert!(Coordinates::new(vec![vec![1], vec![1]], vec![1, 2]).is_err());
    }

    #[test]
    /// Rectangular products compose without expanding their coordinate tuples.
    fn cartesian_nested_order_and_membership() {
        let keys: Vec<_> = (0..4)
            .flat_map(|i| (10..13).map(move |j| vec![i, j]))
            .collect();
        let root = Coordinates::new(keys, (0..12).collect()).unwrap();
        let (view, local) = root.product(vec![vec![3, 1], vec![12, 10]]).unwrap();
        assert_eq!(view.values().unwrap(), [11, 9, 5, 3]);
        assert_eq!(
            (0..local.len())
                .map(|n| local.at(n).unwrap())
                .collect::<Vec<_>>(),
            [11, 9, 5, 3]
        );
        let (nested, positions) = view.product(vec![vec![1, 3], vec![10]]).unwrap();
        assert_eq!(nested.values().unwrap(), [3, 9]);
        assert_eq!([positions.at(0).unwrap(), positions.at(1).unwrap()], [3, 1]);
        assert!(view.product(vec![vec![0], vec![10]]).is_err());
        assert!(view.product(vec![vec![3], vec![11]]).is_err());
        assert_eq!(nested.lookup(&[3, 10]).unwrap(), 1);
        assert!(nested.lookup(&[3, 12]).is_err());
        assert_eq!(nested.id(0).unwrap(), 3);
    }

    #[test]
    /// Duplicate, empty and unknown axes retain the same coordinate semantics.
    fn cartesian_duplicates_empty_and_errors() {
        let root = Coordinates::new(
            vec![vec![0, 5], vec![0, 6], vec![1, 5], vec![1, 6]],
            vec![1, 2, 3, 4],
        )
        .unwrap();
        let (view, _) = root.product(vec![vec![1, 1, 0], vec![6, 6]]).unwrap();
        assert_eq!(view.values().unwrap(), [4, 4, 4, 4, 2, 2]);
        assert_eq!(view.lookup(&[1, 6]).unwrap(), 0);
        assert!(root.product(vec![vec![0], vec![7]]).is_err());
        assert!(root.product(vec![vec![0]]).is_err());
        assert!(root.product(vec![]).is_err());
        assert!(root
            .product(vec![vec![], vec![999]])
            .unwrap()
            .0
            .is_empty()
            .unwrap());
        let empty = Coordinates::<i32>::new(vec![], vec![]).unwrap();
        assert!(empty.product(vec![vec![]]).unwrap().0.is_empty().unwrap());
        assert!(empty.product(vec![]).is_err());
    }

    #[test]
    /// Irregular owners and growth use native lookup while old views stay fixed.
    fn irregular_products_growth_and_lifetime() {
        let root =
            Coordinates::new(vec![vec![0, 5], vec![1, 5], vec![1, 6]], vec![10, 11, 12]).unwrap();
        let weak = Arc::downgrade(&root.table);
        let (view, _) = root.product(vec![vec![1], vec![6, 5]]).unwrap();
        assert_eq!(view.values().unwrap(), [12, 11]);
        root.append(vec![vec![0, 6]], vec![13]).unwrap();
        assert_eq!(
            root.product(vec![vec![0, 1], vec![6]])
                .unwrap()
                .0
                .values()
                .unwrap(),
            [13, 12]
        );
        assert!(view.product(vec![vec![0], vec![6]]).is_err());
        drop(root);
        assert_eq!(view.values().unwrap(), [12, 11]);
        drop(view);
        assert!(weak.upgrade().is_none());
    }

    #[test]
    fn growth_and_selection_share_records_with_fixed_membership() {
        let root = Coordinates::new(vec![vec![1], vec![2]], vec![10, 20]).unwrap();
        let view = root.take(vec![1, 0]).unwrap();
        let full = root.freeze().unwrap();
        root.append(vec![vec![3]], vec![30]).unwrap();
        assert_eq!(root.len().unwrap(), 3);
        assert_eq!(full.len().unwrap(), 2);
        assert_eq!(view.key(0).unwrap(), vec![2]);
        assert_eq!(view.lookup(&[1]).unwrap(), 1);
        assert_eq!(view.lookup_many(&[vec![1], vec![2]]).unwrap(), vec![1, 0]);
        assert!(view.lookup_many(&[vec![3]]).is_err());
        assert!(view.lookup(&[3]).is_err());
        view.set(1, 99).unwrap();
        assert_eq!(root.get(0).unwrap(), 99);
        drop(root);
        assert_eq!(view.get(1).unwrap(), 99);
    }

    #[test]
    fn rejected_batches_are_atomic() {
        let root = Coordinates::new(vec![vec![1]], vec![10]).unwrap();
        assert!(root.append(vec![vec![2], vec![1]], vec![20, 30]).is_err());
        assert!(root.append(vec![vec![2], vec![2]], vec![20, 30]).is_err());
        assert!(root.append(vec![vec![2]], vec![]).is_err());
        assert_eq!(root.len().unwrap(), 1);
        assert!(root.take(vec![1]).is_err());
        assert!(root.key(1).is_err());
        assert!(root.freeze().unwrap().append(vec![], vec![]).is_err());
        assert!(!root.is_empty().unwrap());
    }

    #[test]
    fn views_retain_and_release_the_authoritative_table() {
        let root = Coordinates::new(vec![vec![0], vec![1], vec![2]], vec![4, 5, 6]).unwrap();
        let weak = Arc::downgrade(&root.table);
        let view = root.take(vec![2, 0, 2]).unwrap();
        assert_eq!(view.values().unwrap(), vec![6, 4, 6]);
        assert_eq!(view.lookup(&[2]).unwrap(), 0);
        let nested = view.take(vec![1, 0]).unwrap();
        drop(root);
        drop(view);
        assert_eq!(nested.values().unwrap(), vec![4, 6]);
        assert!(weak.upgrade().is_some());
        drop(nested);
        assert!(weak.upgrade().is_none());
    }

    #[test]
    fn concurrent_growth_keeps_coordinates_and_records_aligned() {
        let root = Coordinates::new(vec![vec![0]], vec![0]).unwrap();
        let writer = root.clone();
        let thread = std::thread::spawn(move || {
            for number in 1..1000 {
                writer.append(vec![vec![number]], vec![number]).unwrap();
            }
        });
        for _ in 0..1000 {
            let frozen = root.freeze().unwrap();
            let last = frozen.len().unwrap() - 1;
            assert_eq!(frozen.key(last).unwrap(), vec![frozen.get(last).unwrap()]);
        }
        thread.join().unwrap();
        assert_eq!(root.values().unwrap(), (0..1000).collect::<Vec<_>>());
    }
}
