//! Rectangular coordinate domains detected once at owner registration.

use crate::{Selector, StorageError};
use std::collections::HashMap;

/// Axis token lookup is proportional to axis lengths, never their product.
#[derive(Debug)]
pub(crate) struct Domain {
    axes: Vec<HashMap<usize, usize>>,
    tokens: Vec<Vec<usize>>,
    shape: Vec<usize>,
    size: usize,
}

impl Domain {
    /// Recognize exact row-major products; arbitrary unions retain native lookup.
    pub(crate) fn infer(keys: &[Vec<usize>]) -> Option<Self> {
        let rank = keys.first()?.len();
        let mut axes = vec![HashMap::new(); rank];
        for key in keys {
            if key.len() != rank {
                return None;
            }
            for (axis, token) in axes.iter_mut().zip(key) {
                let next = axis.len();
                axis.entry(*token).or_insert(next);
            }
        }
        let shape: Vec<_> = axes.iter().map(HashMap::len).collect();
        let size = shape
            .iter()
            .try_fold(1usize, |n, size| n.checked_mul(*size))?;
        if size != keys.len() {
            return None;
        }
        let tokens = axes
            .iter()
            .map(|axis| {
                let mut ordered = vec![0; axis.len()];
                for (token, position) in axis {
                    ordered[*position] = *token;
                }
                ordered
            })
            .collect();
        let domain = Self {
            axes,
            tokens,
            shape,
            size,
        };
        keys.iter()
            .enumerate()
            .all(|(n, key)| domain.lookup(key) == Some(n))
            .then_some(domain)
    }

    /// Build a product without enumerating coordinates; duplicate axes are invalid.
    pub(crate) fn new(tokens: Vec<Vec<usize>>) -> Result<Self, StorageError> {
        let shape: Vec<_> = tokens.iter().map(Vec::len).collect();
        let size = if shape.contains(&0) {
            0
        } else {
            shape
                .iter()
                .try_fold(1usize, |n, size| n.checked_mul(*size))
                .ok_or(StorageError::Length)?
        };
        let axes: Vec<HashMap<_, _>> = tokens
            .iter()
            .map(|axis| {
                axis.iter()
                    .enumerate()
                    .map(|(n, token)| (*token, n))
                    .collect()
            })
            .collect();
        if axes
            .iter()
            .zip(&shape)
            .any(|(axis, size)| axis.len() != *size)
        {
            return Err(StorageError::Index);
        }
        Ok(Self {
            axes,
            tokens,
            shape,
            size,
        })
    }

    /// Count coordinates without allocating their Cartesian product.
    pub(crate) fn len(&self) -> usize {
        self.size
    }

    /// Resolve a coordinate in row-major order, including rank-zero products.
    pub(crate) fn lookup(&self, key: &[usize]) -> Option<usize> {
        if self.size == 0 || key.len() != self.axes.len() {
            return None;
        }
        self.axes.iter().zip(key).try_fold(0, |n, (axis, token)| {
            Some(n * axis.len() + axis.get(token)?)
        })
    }

    /// Decode only the requested coordinate; empty products never divide by zero.
    pub(crate) fn key(&self, position: usize) -> Option<Vec<usize>> {
        if position >= self.size {
            return None;
        }
        let mut rest = position;
        let mut key = vec![0; self.tokens.len()];
        for (n, axis) in self.tokens.iter().enumerate().rev() {
            key[n] = axis[rest % axis.len()];
            rest /= axis.len();
        }
        Some(key)
    }

    /// Return owner and source-local selectors when both domains are products.
    pub(crate) fn select(
        &self,
        requested: &[Vec<usize>],
        source: Option<&Selector>,
        last: bool,
    ) -> Result<Option<(Selector, Selector)>, StorageError> {
        if requested.len() != self.axes.len() {
            return Ok(None);
        }
        let source_axes = match self.source_axes(source) {
            Some(axes) => axes,
            None => return Ok(None),
        };
        let owner = self.owner_axes(requested)?;
        let local = Self::local_axes(&owner, source_axes, last)?;
        let local_shape = source_axes.map_or_else(
            || self.shape.clone(),
            |axes| axes.iter().map(Selector::len).collect(),
        );
        Ok(Some((
            Selector::product(owner, self.shape.clone())?,
            Selector::product(local, local_shape)?,
        )))
    }

    /// Map requested owner-axis IDs back to positions in the source view.
    fn local_axes(
        owner: &[Selector],
        source: Option<&[Selector]>,
        last: bool,
    ) -> Result<Vec<Selector>, StorageError> {
        let Some(axes) = source else {
            return Ok(owner.to_vec());
        };
        owner
            .iter()
            .zip(axes)
            .map(|(requested, axis)| {
                let positions = (0..requested.len())
                    .map(|n| {
                        axis.position_for(requested.at(n)?, last)
                            .ok_or(StorageError::Index)
                    })
                    .collect::<Result<Vec<_>, _>>()?;
                Selector::compact(positions, axis.len())
            })
            .collect()
    }

    /// Distinguish a complete domain, a Cartesian view and an irregular view.
    fn source_axes<'a>(&self, source: Option<&'a Selector>) -> Option<Option<&'a [Selector]>> {
        let bound = self.size;
        match source {
            None => Some(None),
            Some(s) if s.is_full(bound) => Some(None),
            Some(s) => s.product_axes(&self.shape).map(Some),
        }
    }

    /// Resolve per-axis tokens before constructing any full coordinate tuples.
    fn owner_axes(&self, requested: &[Vec<usize>]) -> Result<Vec<Selector>, StorageError> {
        requested
            .iter()
            .zip(&self.axes)
            .map(|(tokens, axis)| {
                let ids = tokens
                    .iter()
                    .map(|token| axis.get(token).copied().ok_or(StorageError::Index))
                    .collect::<Result<Vec<_>, _>>()?;
                Selector::compact(ids, axis.len())
            })
            .collect()
    }
}
