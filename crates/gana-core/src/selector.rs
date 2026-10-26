//! Compact selectors whose membership is fixed at construction.

use crate::StorageError;
use std::collections::HashMap;
use std::sync::Arc;

/// A regular selection needs constant space; irregular selections retain IDs.
#[derive(Clone, Debug)]
pub struct Selector(Selection);

/// Private variants keep arithmetic invariants valid after construction.
#[derive(Clone, Debug)]
enum Selection {
    Span {
        start: usize,
        step: isize,
        len: usize,
    },
    Indices {
        ids: Arc<[usize]>,
        positions: Arc<HashMap<usize, (usize, usize)>>,
    },
    Product {
        axes: Arc<[Selector]>,
        shape: Arc<[usize]>,
        len: usize,
    },
}

impl Selector {
    /// Prefer a constant-sized span when explicit IDs form a progression.
    pub fn compact(ids: Vec<usize>, bound: usize) -> Result<Self, StorageError> {
        if ids.len() < 2 {
            return Self::span(ids.first().copied().unwrap_or(0), 1, ids.len(), bound);
        }
        let step = ids[1] as i128 - ids[0] as i128;
        let regular = step != 0 && ids.windows(2).all(|p| p[1] as i128 - p[0] as i128 == step);
        if regular {
            if let Ok(step) = isize::try_from(step) {
                return Self::span(ids[0], step, ids.len(), bound);
            }
        }
        Self::indices(ids, bound)
    }

    /// Resolve an owner ID to the first local position, preserving duplicates.
    pub fn position(&self, id: usize) -> Option<usize> {
        self.position_for(id, false)
    }

    /// Expressions use the last duplicate; member lookups keep the first.
    pub fn position_for(&self, id: usize, last: bool) -> Option<usize> {
        match &self.0 {
            Selection::Span { start, step, len } => {
                let offset = id as i128 - *start as i128;
                let position = offset / *step as i128;
                (offset % *step as i128 == 0 && position >= 0 && position < *len as i128)
                    .then_some(position as usize)
            }
            Selection::Indices { positions, .. } => {
                positions
                    .get(&id)
                    .map(|pair| if last { pair.1 } else { pair.0 })
            }
            Selection::Product { axes, shape, .. } => Self::product_position(axes, shape, id, last),
        }
    }

    /// Resolve each product digit independently, retaining duplicate policy.
    fn product_position(axes: &[Self], shape: &[usize], id: usize, last: bool) -> Option<usize> {
        let mut remaining = id;
        let mut position = 0usize;
        let mut stride = 1usize;
        for (axis, size) in axes.iter().zip(shape.iter()).rev() {
            if *size == 0 {
                return None;
            }
            position += axis.position_for(remaining % size, last)? * stride;
            remaining /= size;
            stride *= axis.len();
        }
        (remaining == 0).then_some(position)
    }

    /// Retain Cartesian axes separately instead of allocating their product.
    pub fn product(axes: Vec<Selector>, shape: Vec<usize>) -> Result<Self, StorageError> {
        if axes.len() != shape.len() {
            return Err(StorageError::Length);
        }
        let mut len = 1usize;
        let mut bound = 1usize;
        for (axis, size) in axes.iter().zip(&shape) {
            axis.validate(*size)?;
            len = len.checked_mul(axis.len()).ok_or(StorageError::Index)?;
            bound = bound.checked_mul(*size).ok_or(StorageError::Index)?;
        }
        Ok(Self(Selection::Product {
            axes: axes.into(),
            shape: shape.into(),
            len,
        }))
    }

    /// Expose immutable axis selectors for coordinate-domain composition.
    pub fn product_axes(&self, shape: &[usize]) -> Option<&[Selector]> {
        match &self.0 {
            Selection::Product {
                axes, shape: own, ..
            } if own.as_ref() == shape => Some(axes),
            _ => None,
        }
    }

    /// Recognize a frozen complete domain without visiting its members.
    pub fn is_full(&self, bound: usize) -> bool {
        matches!(&self.0, Selection::Span { start: 0, step: 1, len } if *len == bound)
    }

    /// Compose axes or spans directly; compact uncommon irregular compositions.
    pub fn compose(&self, positions: &Self) -> Result<Self, StorageError> {
        positions.validate(self.len())?;
        if self.is_full(self.len()) {
            return Ok(positions.clone());
        }
        if let (
            Selection::Span { start, step, .. },
            Selection::Span {
                start: offset,
                step: stride,
                len,
            },
        ) = (&self.0, &positions.0)
        {
            let first = *start as i128 + *step as i128 * *offset as i128;
            let delta = *step as i128 * *stride as i128;
            if let (Ok(first), Ok(delta)) = (usize::try_from(first), isize::try_from(delta)) {
                return Ok(Self(Selection::Span {
                    start: first,
                    step: delta,
                    len: *len,
                }));
            }
        }
        self.compose_product(positions)
    }

    /// Flatten compatible nested Cartesian selections, keeping depth bounded.
    fn compose_product(&self, positions: &Self) -> Result<Self, StorageError> {
        if let Selection::Product { axes, shape, .. } = &self.0 {
            let local_shape: Vec<_> = axes.iter().map(Selector::len).collect();
            if let Some(local) = positions.product_axes(&local_shape) {
                let composed = axes
                    .iter()
                    .zip(local)
                    .map(|(a, b)| a.compose(b))
                    .collect::<Result<Vec<_>, _>>()?;
                return Self::product(composed, shape.to_vec());
            }
        }
        let ids = (0..positions.len())
            .map(|n| self.at(positions.at(n)?))
            .collect::<Result<Vec<_>, _>>()?;
        // Every ID came from a previously validated selector, so cannot be MAX.
        Self::compact(ids, usize::MAX)
    }
    /// Validate both ends of a progression with checked integer arithmetic.
    pub fn span(start: usize, step: isize, len: usize, bound: usize) -> Result<Self, StorageError> {
        if step == 0 {
            return Err(StorageError::Index);
        }
        if len != 0 {
            let last = (step as i128)
                .checked_mul((len - 1) as i128)
                .and_then(|offset| (start as i128).checked_add(offset))
                .ok_or(StorageError::Index)?;
            if start >= bound || last < 0 || last >= bound as i128 {
                return Err(StorageError::Index);
            }
        }
        Ok(Self(Selection::Span { start, step, len }))
    }

    /// Preserve order and repetition; reject the whole selector on a bad ID.
    pub fn indices(ids: Vec<usize>, bound: usize) -> Result<Self, StorageError> {
        if ids.iter().any(|id| *id >= bound) {
            return Err(StorageError::Index);
        }
        let mut positions = HashMap::new();
        for (position, id) in ids.iter().enumerate() {
            let pair = positions.entry(*id).or_insert((position, position));
            pair.1 = position;
        }
        Ok(Self(Selection::Indices {
            ids: ids.into(),
            positions: Arc::new(positions),
        }))
    }

    /// Revalidate against an owner in O(1) for spans, O(k) for explicit IDs.
    pub fn validate(&self, bound: usize) -> Result<(), StorageError> {
        match &self.0 {
            Selection::Span { start, step, len } => {
                Self::span(*start, *step, *len, bound).map(|_| ())
            }
            Selection::Indices { ids, .. } => {
                if ids.iter().any(|id| *id >= bound) {
                    Err(StorageError::Index)
                } else {
                    Ok(())
                }
            }
            Selection::Product { axes, shape, .. } => {
                let domain = shape
                    .iter()
                    .try_fold(1usize, |n, size| n.checked_mul(*size))
                    .ok_or(StorageError::Index)?;
                if domain > bound && !axes.iter().any(Selector::is_empty) {
                    return Err(StorageError::Index);
                }
                Ok(())
            }
        }
    }

    /// Number of selected members, including repetitions.
    pub fn len(&self) -> usize {
        match &self.0 {
            Selection::Span { len, .. } => *len,
            Selection::Indices { ids, .. } => ids.len(),
            Selection::Product { len, .. } => *len,
        }
    }

    /// Empty selections are valid and contain no member IDs.
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Resolve a position without borrowing an owner's growable vector.
    pub fn at(&self, position: usize) -> Result<usize, StorageError> {
        if position >= self.len() {
            return Err(StorageError::Index);
        }
        match &self.0 {
            Selection::Span { start, step, .. } => {
                Ok((*start as i128 + *step as i128 * position as i128) as usize)
            }
            Selection::Indices { ids, .. } => Ok(ids[position]),
            Selection::Product { axes, shape, .. } => {
                let mut local = position;
                let mut id = 0;
                let mut stride = 1;
                for (axis, size) in axes.iter().zip(shape.iter()).rev() {
                    id += axis.at(local % axis.len())? * stride;
                    local /= axis.len();
                    stride *= size;
                }
                Ok(id)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    /// Product offsets and inverse lookup agree with explicit row-major loops.
    fn product_and_composition_match_explicit_oracle() {
        for rows in [vec![0, 2, 3], vec![3, 1], vec![2, 2, 0], vec![]] {
            for cols in [vec![0, 2], vec![2, 1, 0], vec![1, 1], vec![]] {
                let axes = vec![
                    Selector::compact(rows.clone(), 4).unwrap(),
                    Selector::compact(cols.clone(), 3).unwrap(),
                ];
                let selector = Selector::product(axes, vec![4, 3]).unwrap();
                let expected: Vec<_> = rows
                    .iter()
                    .flat_map(|i| cols.iter().map(move |j| i * 3 + j))
                    .collect();
                assert_eq!(selector.len(), expected.len());
                for (n, id) in expected.iter().enumerate() {
                    assert_eq!(selector.at(n).unwrap(), *id);
                }
                for id in 0..14 {
                    assert_eq!(
                        selector.position(id),
                        expected.iter().position(|v| *v == id)
                    );
                    assert_eq!(
                        selector.position_for(id, true),
                        expected.iter().rposition(|v| *v == id)
                    );
                }
                assert!(selector.at(expected.len()).is_err());
                assert!(selector.validate(12).is_ok());
                if !expected.is_empty() {
                    assert!(selector.validate(11).is_err());
                }
            }
        }
    }

    #[test]
    /// Nested product axes flatten; irregular compositions remain valid and ordered.
    fn nested_product_and_irregular_composition() {
        let original = Selector::product(
            vec![
                Selector::span(3, -1, 4, 4).unwrap(),
                Selector::span(0, 2, 2, 3).unwrap(),
            ],
            vec![4, 3],
        )
        .unwrap();
        let local = Selector::product(
            vec![
                Selector::span(1, 2, 2, 4).unwrap(),
                Selector::span(1, 1, 1, 2).unwrap(),
            ],
            vec![4, 2],
        )
        .unwrap();
        let nested = original.compose(&local).unwrap();
        assert!(nested.product_axes(&[4, 3]).is_some());
        assert_eq!([nested.at(0).unwrap(), nested.at(1).unwrap()], [8, 2]);
        let irregular = original
            .compose(&Selector::indices(vec![7, 0, 3], 8).unwrap())
            .unwrap();
        assert_eq!(
            (0..3).map(|n| irregular.at(n).unwrap()).collect::<Vec<_>>(),
            [2, 9, 8]
        );
        assert_eq!(irregular.position(8), Some(2));
        assert_eq!(irregular.position(10), None);
        assert!(original
            .compose(&Selector::span(8, 1, 1, 9).unwrap())
            .is_err());
        assert!(Selector::product(vec![], vec![1]).is_err());
        assert!(Selector::product(
            vec![Selector::span(0, 1, 0, 0).unwrap(); 2],
            vec![usize::MAX; 2]
        )
        .is_err());
    }
}
