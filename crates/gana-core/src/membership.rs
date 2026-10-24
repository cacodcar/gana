//! An optional inverted index over immutable affine row occurrences.

use crate::Affine;
use std::collections::HashMap;
use std::mem::size_of;

/// Row positions keyed by owner slot and stable owner-local member ID.
///
/// Explicit zero terms still represent membership. Repeated terms in one row
/// produce one link; repeated selected rows keep their distinct local positions.
#[derive(Debug)]
pub struct Membership {
    rows: HashMap<(usize, usize), Vec<usize>>,
}

impl Membership {
    /// Build once when metadata is requested, without creating Python objects.
    pub fn new(batch: &Affine) -> Self {
        let mut rows: HashMap<(usize, usize), Vec<usize>> = HashMap::new();
        for (position, row) in batch.rows().enumerate() {
            for term in &row.terms {
                let positions = rows.entry((term.owner, term.member)).or_default();
                if positions.last() != Some(&position) {
                    positions.push(position);
                }
            }
        }
        Self { rows }
    }

    /// Return matching local row positions in insertion order.
    pub fn rows(&self, owner: usize, member: usize) -> &[usize] {
        self.rows.get(&(owner, member)).map_or(&[], Vec::as_slice)
    }

    /// Estimate reserved key/value and row-index buffers, excluding allocator
    /// overhead, hash control bytes, the object header and Python wrappers.
    pub fn buffer_bytes(&self) -> usize {
        self.rows.capacity() * size_of::<((usize, usize), Vec<usize>)>()
            + self
                .rows
                .values()
                .map(|positions| positions.capacity() * size_of::<usize>())
                .sum::<usize>()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Number, Row, Term};

    /// Include cancellation, repeated terms and independent owner namespaces.
    fn batch() -> Affine {
        let row = |ids: &[(usize, usize, i128)]| Row {
            terms: ids
                .iter()
                .map(|&(owner, member, coefficient)| Term {
                    owner,
                    member,
                    column: member,
                    coefficient: Number::Integer(coefficient),
                })
                .collect(),
            offset: Number::Integer(0),
        };
        Affine::new(vec![
            row(&[(0, 4, 1), (1, 4, 0), (0, 4, -1)]),
            row(&[(0, 9, 2)]),
            row(&[(0, 4, 0), (0, 9, 3)]),
        ])
    }

    /// Repeated terms are one link; zeros and separate owners still count.
    #[test]
    fn repeated_terms_and_zero_coefficients_keep_ordered_membership() {
        let index = Membership::new(&batch());
        assert_eq!(index.rows(0, 4), &[0, 2]);
        assert_eq!(index.rows(0, 9), &[1, 2]);
        assert_eq!(index.rows(1, 4), &[0]);
        assert!(index.rows(1, 9).is_empty());
        assert!(index.rows(usize::MAX, usize::MAX).is_empty());
    }

    /// A selected occurrence uses its output position, including repeated rows.
    #[test]
    fn selected_repeated_rows_have_distinct_local_positions() {
        let selected = batch().take(vec![2, 0, 2]).unwrap();
        let index = Membership::new(&selected);
        assert_eq!(index.rows(0, 4), &[0, 1, 2]);
        assert_eq!(index.rows(0, 9), &[0, 2]);
        assert_eq!(index.rows(1, 4), &[1]);
    }

    /// Empty batches allow any absent membership query.
    #[test]
    fn empty_batches_have_no_memberships() {
        let index = Membership::new(&Affine::new(vec![]));
        assert!(index.rows(0, 0).is_empty());
    }
}
