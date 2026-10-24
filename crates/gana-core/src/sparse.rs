//! Checked compressed rows compiled directly from immutable affine batches.

use crate::{Affine, AlgebraError, Number};

/// Per-batch, per-owner optional columns indexed by captured member identity.
pub type ColumnMaps = Vec<Vec<Option<Vec<usize>>>>;

/// Own sparse numeric buffers; no Python members or model references are retained.
#[derive(Debug)]
pub struct Sparse {
    pub columns: usize,
    pub indptr: Vec<usize>,
    pub indices: Vec<usize>,
    pub data: Vec<Number>,
    pub rhs: Vec<Number>,
}

impl Sparse {
    /// Accumulate duplicate columns in occurrence order, retaining explicit zeros.
    pub fn compile(batches: &[&Affine], columns: usize) -> Result<Self, AlgebraError> {
        Self::compile_for(batches, columns, None, Number::Integer(1))
    }

    /// Compile one symbol space without materializing or copying affine rows.
    pub fn compile_for(
        batches: &[&Affine],
        columns: usize,
        owners: Option<&[Vec<bool>]>,
        factor: Number,
    ) -> Result<Self, AlgebraError> {
        Self::compile_mapped(batches, columns, owners, factor, None)
    }

    /// Resolve anonymous columns at export without rewriting shared batches.
    pub fn compile_mapped(
        batches: &[&Affine],
        columns: usize,
        owners: Option<&[Vec<bool>]>,
        factor: Number,
        mappings: Option<&ColumnMaps>,
    ) -> Result<Self, AlgebraError> {
        if owners.is_some_and(|masks| masks.len() != batches.len()) {
            return Err(AlgebraError::Shape);
        }
        if mappings.is_some_and(|maps| maps.len() != batches.len()) {
            return Err(AlgebraError::Shape);
        }
        let mut result = Self {
            columns,
            indptr: vec![0],
            indices: vec![],
            data: vec![],
            rhs: vec![],
        };
        for (index, batch) in batches.iter().enumerate() {
            let mask = owners.map(|masks| masks[index].as_slice());
            let mapping = mappings.map(|maps| maps[index].as_slice());
            result.append(batch, mask, factor, mapping)?;
        }
        Ok(result)
    }

    /// Append one checked batch, preserving row and term encounter order.
    fn append(
        &mut self,
        batch: &Affine,
        owners: Option<&[bool]>,
        factor: Number,
        mapping: Option<&[Option<Vec<usize>>]>,
    ) -> Result<(), AlgebraError> {
        for (position, row) in batch.rows().enumerate() {
            for (column, value) in batch.matrix_mapped(position, owners, factor, mapping)? {
                if column >= self.columns {
                    return Err(AlgebraError::Index);
                }
                self.indices.push(column);
                self.data.push(value);
            }
            self.indptr.push(self.data.len());
            self.rhs.push(row.offset.multiply(Number::Integer(-1))?);
        }
        Ok(())
    }

    /// Count allocated vector capacity, excluding the struct and allocator overhead.
    pub fn reserved_bytes(&self) -> usize {
        (self.indptr.capacity() + self.indices.capacity()) * size_of::<usize>()
            + (self.data.capacity() + self.rhs.capacity()) * size_of::<Number>()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Row, Term};

    #[test]
    /// Deferred columns follow owner/member identity, not provisional numbers.
    fn late_columns_preserve_repeated_terms_and_selection() {
        let source = Affine::variables(vec![(0, 0), (1, 1)]);
        let mixed = source.combine(&source, (&[0], &[1]), "sub").unwrap();
        let selected = mixed.take(vec![1, 0, 1]).unwrap();
        let maps = vec![vec![None, Some(vec![3, 2])]];
        let mask = vec![vec![false, true]];
        let result = Sparse::compile_mapped(
            &[&selected],
            4,
            Some(&mask),
            Number::Integer(-1),
            Some(&maps),
        )
        .unwrap();
        assert_eq!(result.indices, vec![2, 3, 2]);
        assert_eq!(result.data, vec![Number::Integer(1); 3]);
        assert_eq!(result.indptr, vec![0, 1, 2, 3]);
        // The shared source still contains its construction-time columns.
        assert_eq!(source.matrix(1).unwrap(), vec![(1, Number::Integer(1))]);
        let collision = vec![vec![Some(vec![2, 3]), Some(vec![2, 3])]];
        let cancelled =
            Sparse::compile_mapped(&[&mixed], 4, None, Number::Integer(1), Some(&collision))
                .unwrap();
        assert_eq!(cancelled.indices, vec![2, 3]);
        assert_eq!(cancelled.data, vec![Number::Integer(0); 2]);
    }

    #[test]
    /// Malformed late maps fail at batch, owner, member and column boundaries.
    fn late_columns_validate_every_mapping_dimension() {
        let source = Affine::variables(vec![(1, 0)]);
        let factor = Number::Integer(1);
        assert_eq!(
            Sparse::compile_mapped(&[&source], 2, None, factor, Some(&vec![])).unwrap_err(),
            AlgebraError::Shape,
        );
        for maps in [
            vec![vec![]],
            vec![vec![Some(vec![0])]],
            vec![vec![Some(vec![0, 2])]],
        ] {
            assert_eq!(
                Sparse::compile_mapped(&[&source], 2, None, factor, Some(&maps)).unwrap_err(),
                AlgebraError::Index,
            );
        }
        // A projected-out owner cannot use or overflow a late column.
        let ignored = Sparse::compile_mapped(
            &[&source],
            0,
            Some(&[vec![false]]),
            factor,
            Some(&vec![vec![]]),
        )
        .unwrap();
        assert!(ignored.data.is_empty());
    }

    #[test]
    /// Independent column spaces are projected before accumulation and negation.
    fn owner_projection_preserves_theta_signs_and_checks_masks() {
        let variables = Affine::variables(vec![(0, 0), (1, 1)]);
        let thetas = Affine::variables(vec![(0, 0), (1, 1)]);
        let mixed = variables.combine(&thetas, (&[0], &[1]), "sub").unwrap();
        let masks = vec![vec![false, true]];
        let rhs = Sparse::compile_for(&[&mixed], 2, Some(&masks), Number::Integer(-1)).unwrap();
        assert_eq!(rhs.indices, vec![0, 1]);
        assert_eq!(rhs.data, vec![Number::Integer(1); 2]);
        assert_eq!(rhs.indptr, vec![0, 1, 2]);
        assert_eq!(
            Sparse::compile_for(&[&mixed], 2, Some(&[]), Number::Integer(1)).unwrap_err(),
            AlgebraError::Shape
        );
        assert_eq!(
            mixed.matrix_for(0, Some(&[true]), Number::Integer(1)),
            Err(AlgebraError::Index)
        );
    }

    #[test]
    /// Theta-left normalization preserves right-before-left occurrence order.
    fn reversed_subtraction_and_projection_overflow() {
        let a = row(0, &[3], 0);
        let b = row(0, &[5], 2);
        let mixed = a.combine(&b, (&[0], &[1]), "rsub").unwrap();
        assert_eq!(mixed.row(0).unwrap().terms[0].owner, 1);
        assert_eq!(
            mixed.row(0).unwrap().terms[0].coefficient,
            Number::Integer(-5)
        );
        assert_eq!(mixed.matrix(0).unwrap(), vec![(0, Number::Integer(-2))]);
        assert_eq!(mixed.row(0).unwrap().offset, Number::Integer(-2));
        let minimum = row(0, &[i128::MIN], 0);
        assert_eq!(
            minimum.matrix_for(0, Some(&[true]), Number::Integer(-1)),
            Err(AlgebraError::Overflow)
        );
        assert!(minimum
            .matrix_for(0, Some(&[false]), Number::Integer(-1))
            .unwrap()
            .is_empty());
    }

    /// Construct a row with repeated column occurrences and an exact offset.
    fn row(column: usize, values: &[i128], offset: i128) -> Affine {
        Affine::new(vec![Row {
            terms: values
                .iter()
                .map(|value| Term {
                    owner: 0,
                    member: 0,
                    column,
                    coefficient: Number::Integer(*value),
                })
                .collect(),
            offset: Number::Integer(offset),
        }])
    }

    #[test]
    fn compile_preserves_batch_order_cancellation_and_exact_integers() {
        let first = row(2, &[3, -3], -5);
        let second = row(0, &[1 << 60, 1], 7);
        let result = Sparse::compile(&[&first, &second], 4).unwrap();
        assert_eq!(result.indptr, vec![0, 1, 2]);
        assert_eq!(result.indices, vec![2, 0]);
        assert_eq!(
            result.data,
            vec![Number::Integer(0), Number::Integer((1 << 60) + 1)]
        );
        assert_eq!(result.rhs, vec![Number::Integer(5), Number::Integer(-7)]);
        assert!(result.reserved_bytes() > 0);
    }

    #[test]
    fn empty_and_constant_rows_preserve_shape() {
        let empty = Sparse::compile(&[], 9).unwrap();
        assert_eq!(empty.indptr, vec![0]);
        assert_eq!(empty.columns, 9);
        let constants = Affine::constants(vec![Number::Integer(4)]);
        let result = Sparse::compile(&[&constants], 0).unwrap();
        assert_eq!(result.indptr, vec![0, 0]);
        assert_eq!(result.rhs, vec![Number::Integer(-4)]);
    }

    #[test]
    fn invalid_columns_and_overflow_fail_without_partial_export() {
        assert_eq!(
            Sparse::compile(&[&row(3, &[1], 0)], 3).unwrap_err(),
            AlgebraError::Index
        );
        assert_eq!(
            Sparse::compile(&[&row(0, &[i128::MAX, 1], 0)], 1).unwrap_err(),
            AlgebraError::Overflow
        );
        assert_eq!(
            Sparse::compile(&[&row(0, &[1], i128::MIN)], 1).unwrap_err(),
            AlgebraError::Overflow
        );
    }
}
