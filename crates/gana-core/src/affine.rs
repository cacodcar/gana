//! Immutable affine batches. Arithmetic never calls Python or creates members.

use crate::Selector;
use std::collections::HashMap;
use std::sync::Arc;

/// Preserve integer arithmetic until overflow asks the frontend to fall back.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Number {
    Integer(i128),
    Real(f64),
}

/// Unsupported sizes and integer overflow are recoverable frontend fallbacks.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum AlgebraError {
    Overflow,
    Shape,
    Nonlinear,
    Index,
}

impl Number {
    /// Convert only when Python would mix an integer with a floating value.
    pub fn real(self) -> f64 {
        match self {
            Self::Integer(value) => value as f64,
            Self::Real(value) => value,
        }
    }

    /// Keep exact integer addition; never silently narrow an overflowing result.
    pub fn checked_add(self, other: Self) -> Result<Self, AlgebraError> {
        match (self, other) {
            (Self::Integer(a), Self::Integer(b)) => a
                .checked_add(b)
                .map(Self::Integer)
                .ok_or(AlgebraError::Overflow),
            _ => Ok(Self::Real(self.real() + other.real())),
        }
    }

    /// Preserve Python's integer-versus-real product semantics.
    pub fn multiply(self, other: Self) -> Result<Self, AlgebraError> {
        match (self, other) {
            (Self::Integer(a), Self::Integer(b)) => a
                .checked_mul(b)
                .map(Self::Integer)
                .ok_or(AlgebraError::Overflow),
            _ => Ok(Self::Real(self.real() * other.real())),
        }
    }
}

/// An occurrence retains owner-local identity and the global solver column.
#[derive(Clone, Debug, PartialEq)]
pub struct Term {
    pub owner: usize,
    pub member: usize,
    pub column: usize,
    pub coefficient: Number,
}

/// A row stores its ordinary additive offset (the negative of legacy F.B).
#[derive(Clone, Debug, PartialEq)]
pub struct Row {
    pub terms: Vec<Term>,
    pub offset: Number,
}

impl Row {
    /// Scale a detached row while translating source-owner slots once per term.
    fn scaled(&self, factor: Number, owners: &[usize]) -> Result<Self, AlgebraError> {
        let terms = self
            .terms
            .iter()
            .map(|term| {
                Ok(Term {
                    owner: *owners.get(term.owner).ok_or(AlgebraError::Index)?,
                    coefficient: factor.multiply(term.coefficient)?,
                    ..term.clone()
                })
            })
            .collect::<Result<_, _>>()?;
        Ok(Self {
            terms,
            offset: factor.multiply(self.offset)?,
        })
    }

    /// Append terms without dropping repeated or cancelled variable occurrences.
    fn plus(mut self, other: Self) -> Result<Self, AlgebraError> {
        self.offset = self.offset.checked_add(other.offset)?;
        self.terms.extend(other.terms);
        Ok(self)
    }
}

/// Clones share immutable rows; each new operation owns only its resulting batch.
#[derive(Clone, Debug)]
pub struct Affine {
    rows: Arc<[Row]>,
    selection: Selector,
}

impl Affine {
    /// Retain a validated batch without an expression interning cache.
    pub fn new(rows: Vec<Row>) -> Self {
        let selection = Selector::span(0, 1, rows.len(), rows.len())
            .expect("a complete affine batch is a valid span");
        Self {
            rows: rows.into(),
            selection,
        }
    }

    /// Build numeric rows, retaining the exact input number kind.
    pub fn constants(values: Vec<Number>) -> Self {
        Self::new(
            values
                .into_iter()
                .map(|offset| Row {
                    terms: vec![],
                    offset,
                })
                .collect(),
        )
    }

    /// Convert a coherent native member batch to unit-coefficient rows.
    pub fn variables(records: Vec<(usize, usize)>) -> Self {
        Self::new(
            records
                .into_iter()
                .map(|(member, column)| Row {
                    terms: vec![Term {
                        owner: 0,
                        member,
                        column,
                        coefficient: Number::Integer(1),
                    }],
                    offset: Number::Integer(0),
                })
                .collect(),
        )
    }

    /// Read selected immutable rows in order without cloning coefficient buffers.
    pub fn rows(&self) -> impl ExactSizeIterator<Item = &Row> {
        (0..self.len()).map(|position| {
            self.row(position)
                .expect("affine selectors are validated at construction")
        })
    }

    /// Count selected rows, including repeated occurrences.
    pub fn len(&self) -> usize {
        self.selection.len()
    }

    /// Empty selections remain valid immutable batches.
    pub fn is_empty(&self) -> bool {
        self.selection.is_empty()
    }

    /// Resolve a local row through the validated selector into shared storage.
    pub fn row(&self, position: usize) -> Result<&Row, AlgebraError> {
        let id = self
            .selection
            .at(position)
            .map_err(|_| AlgebraError::Index)?;
        self.rows.get(id).ok_or(AlgebraError::Index)
    }

    /// Share row and term ownership; flatten nested selections into one selector.
    pub fn take(&self, positions: Vec<usize>) -> Result<Self, AlgebraError> {
        let local = Selector::compact(positions, self.len()).map_err(|_| AlgebraError::Index)?;
        self.select(&local)
    }

    /// Compose a compact coordinate selector without expanding its positions.
    pub fn select(&self, local: &Selector) -> Result<Self, AlgebraError> {
        let selection = self
            .selection
            .compose(local)
            .map_err(|_| AlgebraError::Index)?;
        Ok(Self {
            rows: self.rows.clone(),
            selection,
        })
    }

    /// Align divisible row counts by consecutive repeats, matching Gana.
    fn aligned(&self, position: usize, total: usize) -> &Row {
        self.row(position / (total / self.len()))
            .expect("aligned position is bounded by the validated row count")
    }

    /// Validate both lengths before constructing any output rows.
    fn length(&self, other: &Self) -> Result<usize, AlgebraError> {
        let a = self.len();
        let b = other.len();
        if a == 0 || b == 0 || (a % b != 0 && b % a != 0) {
            return Err(AlgebraError::Shape);
        }
        Ok(a.max(b))
    }

    /// Compute one aligned affine operation using mapped owner identities.
    fn combine_row(
        a: &Row,
        b: &Row,
        owners: (&[usize], &[usize]),
        operation: &str,
    ) -> Result<Row, AlgebraError> {
        match operation {
            "add" => a
                .scaled(Number::Integer(1), owners.0)?
                .plus(b.scaled(Number::Integer(1), owners.1)?),
            "sub" => a
                .scaled(Number::Integer(1), owners.0)?
                .plus(b.scaled(Number::Integer(-1), owners.1)?),
            // Theta-left subtraction normalizes to -right + left in Python.
            "rsub" => b
                .scaled(Number::Integer(-1), owners.1)?
                .plus(a.scaled(Number::Integer(1), owners.0)?),
            "mul" if a.terms.is_empty() => b.scaled(a.offset, owners.1),
            "mul" if b.terms.is_empty() => a.scaled(b.offset, owners.0),
            _ => Err(AlgebraError::Nonlinear),
        }
    }

    /// Perform the complete arithmetic batch within Rust.
    pub fn combine(
        &self,
        other: &Self,
        owners: (&[usize], &[usize]),
        operation: &str,
    ) -> Result<Self, AlgebraError> {
        let total = self.length(other)?;
        let rows = (0..total)
            .map(|position| {
                Self::combine_row(
                    self.aligned(position, total),
                    other.aligned(position, total),
                    owners,
                    operation,
                )
            })
            .collect::<Result<_, _>>()?;
        Ok(Self::new(rows))
    }

    /// Reduce explicit groups; nonzero real offsets retain Python's sum policy.
    ///
    /// Python 3.12+ uses compensated real summation. Such offsets deliberately
    /// fall back rather than silently changing floating-point accumulation.
    pub fn sum(&self, groups: &[Vec<usize>]) -> Result<Self, AlgebraError> {
        let rows = groups
            .iter()
            .map(|group| self.sum_group(group))
            .collect::<Result<_, _>>()?;
        Ok(Self::new(rows))
    }

    /// Reduce term occurrences alone when Python must supply numeric offsets.
    pub fn sum_terms(&self, groups: &[Vec<usize>]) -> Result<Self, AlgebraError> {
        self.sum_with_offsets(groups, vec![Number::Integer(0); groups.len()])
    }

    /// Attach interpreter-computed offsets while copying each term only once.
    pub fn sum_with_offsets(
        &self,
        groups: &[Vec<usize>],
        offsets: Vec<Number>,
    ) -> Result<Self, AlgebraError> {
        if groups.len() != offsets.len() {
            return Err(AlgebraError::Shape);
        }
        let rows = groups
            .iter()
            .zip(offsets)
            .map(|(positions, offset)| {
                let mut terms = Vec::new();
                for position in positions {
                    let row = self.row(*position)?;
                    terms.extend(row.terms.iter().cloned());
                }
                Ok(Row { terms, offset })
            })
            .collect::<Result<_, _>>()?;
        Ok(Self::new(rows))
    }

    /// Replace offsets after a frontend-compatible numeric reduction.
    pub fn with_offsets(&self, values: Vec<Number>) -> Result<Self, AlgebraError> {
        if values.len() != self.len() {
            return Err(AlgebraError::Shape);
        }
        Ok(Self::new(
            self.rows()
                .zip(values)
                .map(|(row, offset)| Row {
                    terms: row.terms.clone(),
                    offset,
                })
                .collect(),
        ))
    }

    /// Concatenate a group's sparse occurrences and add exact integer offsets.
    fn sum_group(&self, positions: &[usize]) -> Result<Row, AlgebraError> {
        let mut result = Row {
            terms: vec![],
            offset: Number::Integer(0),
        };
        let mut saw_real = false;
        for position in positions {
            let row = self.row(*position)?;
            if matches!(row.offset, Number::Real(_)) {
                saw_real = true;
            }
            if saw_real && (row.offset.real() != 0.0 || result.offset.real() != 0.0) {
                return Err(AlgebraError::Overflow);
            }
            result = result.plus(row.clone())?;
        }
        Ok(result)
    }

    /// Accumulate repeated columns in encounter order, including explicit zeros.
    pub fn matrix(&self, position: usize) -> Result<Vec<(usize, Number)>, AlgebraError> {
        self.matrix_for(position, None, Number::Integer(1))
    }

    /// Project owner slots into one column space before accumulating terms.
    ///
    /// Variable and theta columns have independent numbering. The frontend
    /// supplies their owner mask; RHS theta signs are applied per occurrence,
    /// before addition, matching compatibility rows even for repeated columns.
    pub fn matrix_for(
        &self,
        position: usize,
        owners: Option<&[bool]>,
        factor: Number,
    ) -> Result<Vec<(usize, Number)>, AlgebraError> {
        self.matrix_mapped(position, owners, factor, None)
    }

    /// Resolve deferred owner-local IDs only when exporting solver columns.
    /// A missing owner map keeps the captured column of a registered symbol.
    pub fn matrix_mapped(
        &self,
        position: usize,
        owners: Option<&[bool]>,
        factor: Number,
        columns: Option<&[Option<Vec<usize>>]>,
    ) -> Result<Vec<(usize, Number)>, AlgebraError> {
        let row = self.row(position)?;
        let mut positions = HashMap::new();
        let mut values: Vec<(usize, Number)> = Vec::new();
        for term in &row.terms {
            if let Some(mask) = owners {
                if !*mask.get(term.owner).ok_or(AlgebraError::Index)? {
                    continue;
                }
            }
            let column = term.resolve_column(columns)?;
            let index = *positions.entry(column).or_insert_with(|| {
                values.push((column, Number::Integer(0)));
                values.len() - 1
            });
            values[index].1 = values[index]
                .1
                .checked_add(factor.multiply(term.coefficient)?)?;
        }
        Ok(values)
    }
}

impl Term {
    /// Validate both owner and member before using a late column assignment.
    fn resolve_column(
        &self,
        columns: Option<&[Option<Vec<usize>>]>,
    ) -> Result<usize, AlgebraError> {
        let Some(columns) = columns else {
            return Ok(self.column);
        };
        match columns.get(self.owner).ok_or(AlgebraError::Index)? {
            None => Ok(self.column),
            Some(mapping) => mapping.get(self.member).copied().ok_or(AlgebraError::Index),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    /// Coordinate selectors share rows; compensated offsets need one value per group.
    fn coordinate_selection_and_supplied_offsets_are_checked() {
        let source = Affine::variables((0..6).map(|n| (n, n)).collect());
        let selector = Selector::product(
            vec![
                Selector::indices(vec![1, 0], 2).unwrap(),
                Selector::span(0, 2, 2, 3).unwrap(),
            ],
            vec![2, 3],
        )
        .unwrap();
        let selected = source.select(&selector).unwrap();
        assert!(Arc::ptr_eq(&source.rows, &selected.rows));
        assert_eq!(
            selected
                .rows()
                .map(|r| r.terms[0].column)
                .collect::<Vec<_>>(),
            [3, 5, 0, 2]
        );
        assert!(source.select(&Selector::span(6, 1, 1, 7).unwrap()).is_err());
        let reduced = selected
            .sum_with_offsets(&[vec![3, 1]], vec![Number::Real(1.25)])
            .unwrap();
        assert_eq!(reduced.row(0).unwrap().offset, Number::Real(1.25));
        assert_eq!(
            reduced
                .row(0)
                .unwrap()
                .terms
                .iter()
                .map(|t| t.column)
                .collect::<Vec<_>>(),
            [2, 5]
        );
        assert!(selected.sum_with_offsets(&[vec![0]], vec![]).is_err());
        assert!(selected
            .sum_with_offsets(&[vec![4]], vec![Number::Integer(0)])
            .is_err());
    }

    /// Two columns include a repeated global ID to test accumulation separately.
    fn variables() -> Affine {
        Affine::variables(vec![(4, 7), (9, 7)])
    }

    #[test]
    fn weighted_reduction_preserves_repeated_columns() {
        let weights = Affine::constants(vec![Number::Integer(2), Number::Integer(-5)]);
        let result = weights.combine(&variables(), (&[], &[3]), "mul").unwrap();
        let reduced = result.sum(&[vec![0, 1]]).unwrap();
        assert_eq!(reduced.matrix(0).unwrap(), vec![(7, Number::Integer(-3))]);
        assert_eq!(reduced.row(0).unwrap().terms[1].member, 9);
        assert_eq!(reduced.row(0).unwrap().terms[1].owner, 3);
    }

    #[test]
    fn consecutive_broadcast_and_constants() {
        let weights = Affine::constants(vec![Number::Integer(2), Number::Integer(3)]);
        let values = Affine::variables((0..4).map(|n| (n, n)).collect());
        let scaled = weights.combine(&values, (&[], &[0]), "mul").unwrap();
        let constant = Affine::constants(vec![Number::Integer(7)]);
        let result = scaled.combine(&constant, (&[0], &[]), "sub").unwrap();
        let expected = [2, 2, 3, 3];
        for (row, coefficient) in result.rows().zip(expected) {
            assert_eq!(row.terms[0].coefficient, Number::Integer(coefficient));
            assert_eq!(row.offset, Number::Integer(-7));
        }
    }

    #[test]
    fn cancellation_retains_explicit_zero_columns() {
        let result = variables()
            .combine(&variables(), (&[0], &[0]), "sub")
            .unwrap();
        assert_eq!(result.matrix(1).unwrap(), vec![(7, Number::Integer(0))]);
        assert_eq!(result.row(1).unwrap().terms.len(), 2);
    }

    #[test]
    fn integer_overflow_never_narrows_silently() {
        assert_eq!(
            Number::Integer(i128::MAX).checked_add(Number::Integer(1)),
            Err(AlgebraError::Overflow)
        );
        assert_eq!(
            Number::Integer(i128::MAX).multiply(Number::Integer(2)),
            Err(AlgebraError::Overflow)
        );
        assert_eq!(
            Number::Integer(1 << 60)
                .checked_add(Number::Integer(1))
                .unwrap(),
            Number::Integer((1 << 60) + 1)
        );
    }

    #[test]
    fn mixed_real_arithmetic_matches_python_promotion() {
        assert_eq!(
            Number::Integer(3).multiply(Number::Real(0.5)).unwrap(),
            Number::Real(1.5)
        );
        assert_eq!(
            Number::Real(0.5).checked_add(Number::Integer(2)).unwrap(),
            Number::Real(2.5)
        );
    }

    #[test]
    fn invalid_shapes_and_nonlinearity_are_rejected() {
        let empty = Affine::constants(vec![]);
        assert_eq!(empty.length(&variables()), Err(AlgebraError::Shape));
        let triple = Affine::constants(vec![Number::Integer(1); 3]);
        assert_eq!(triple.length(&variables()), Err(AlgebraError::Shape));
        assert_eq!(
            variables()
                .combine(&variables(), (&[0], &[0]), "mul")
                .unwrap_err(),
            AlgebraError::Nonlinear
        );
        assert_eq!(
            variables()
                .combine(&variables(), (&[], &[0]), "add")
                .unwrap_err(),
            AlgebraError::Index
        );
    }

    #[test]
    fn reduction_bounds_and_compensated_float_fallback() {
        assert_eq!(
            variables().sum(&[vec![5]]).unwrap_err(),
            AlgebraError::Index
        );
        assert_eq!(variables().matrix(5), Err(AlgebraError::Index));
        let real = Affine::constants(vec![Number::Real(0.1)]);
        assert_eq!(real.sum(&[vec![0]]).unwrap_err(), AlgebraError::Overflow);
        let zero = Affine::constants(vec![Number::Real(0.0)]);
        assert_eq!(
            zero.sum(&[vec![0]]).unwrap().row(0).unwrap().offset,
            Number::Real(0.0)
        );
    }

    #[test]
    fn term_reduction_accepts_frontend_offsets_without_touching_inputs() {
        let input = variables();
        let reduced = input.sum_terms(&[vec![1, 0]]).unwrap();
        let updated = reduced.with_offsets(vec![Number::Real(0.25)]).unwrap();
        assert_eq!(updated.row(0).unwrap().offset, Number::Real(0.25));
        assert_eq!(updated.row(0).unwrap().terms[0].member, 9);
        assert_eq!(input.len(), 2);
        assert_eq!(input.with_offsets(vec![]).unwrap_err(), AlgebraError::Shape);
        assert_eq!(
            input.sum_terms(&[vec![2]]).unwrap_err(),
            AlgebraError::Index
        );
    }

    #[test]
    fn mixed_zero_and_nonzero_offsets_request_python_summation() {
        let input = Affine::constants(vec![
            Number::Integer(1 << 60),
            Number::Real(0.0),
            Number::Integer(1),
        ]);
        assert_eq!(
            input.sum(&[vec![0, 1, 2]]).unwrap_err(),
            AlgebraError::Overflow
        );
    }

    /// Nested views retain row identity after the original handle is dropped.
    #[test]
    fn selections_share_rows_and_preserve_order_repetition_and_lifetime() {
        let original = Affine::variables((0..6).map(|n| (n, n)).collect());
        let reverse = original.take(vec![5, 3, 1]).unwrap();
        let nested = reverse.take(vec![2, 0, 2]).unwrap();
        assert!(Arc::ptr_eq(&original.rows, &nested.rows));
        assert!(std::ptr::eq(
            original.row(1).unwrap(),
            nested.row(0).unwrap()
        ));
        drop(original);
        drop(reverse);
        let columns: Vec<_> = nested.rows().map(|row| row.terms[0].column).collect();
        assert_eq!(columns, vec![1, 5, 1]);
        assert_eq!(
            nested.sum(&[vec![0, 1, 2]]).unwrap().matrix(0).unwrap(),
            vec![(1, Number::Integer(2)), (5, Number::Integer(1))]
        );
    }

    /// All readers and arithmetic use local selection order, never owner order.
    #[test]
    fn selected_arithmetic_offsets_and_sparse_export_use_local_rows() {
        let input = variables().take(vec![1, 0, 1]).unwrap();
        let weights = Affine::constants(vec![
            Number::Integer(2),
            Number::Integer(3),
            Number::Integer(4),
        ]);
        let scaled = input.combine(&weights, (&[0], &[]), "mul").unwrap();
        let updated = scaled.with_offsets(vec![Number::Integer(5); 3]).unwrap();
        let sparse = crate::Sparse::compile(&[&updated], 8).unwrap();
        assert_eq!(
            sparse.data,
            vec![Number::Integer(2), Number::Integer(3), Number::Integer(4)]
        );
        assert_eq!(sparse.rhs, vec![Number::Integer(-5); 3]);
        assert_eq!(
            input
                .sum_terms(&[vec![0, 2]])
                .unwrap()
                .row(0)
                .unwrap()
                .terms[1]
                .member,
            9
        );
    }

    /// Invalid nested IDs fail before publication; empty views stay empty.
    #[test]
    fn invalid_selection_is_atomic_and_empty_selection_is_valid() {
        let input = variables();
        assert_eq!(input.take(vec![0, 2]).unwrap_err(), AlgebraError::Index);
        assert_eq!(input.row(2).unwrap_err(), AlgebraError::Index);
        assert_eq!(input.len(), 2);
        let empty = input.take(vec![]).unwrap();
        assert!(empty.is_empty());
        assert!(empty.take(vec![]).unwrap().is_empty());
        assert_eq!(empty.take(vec![0]).unwrap_err(), AlgebraError::Index);
        assert_eq!(empty.rows().count(), 0);
    }
}
