//! Batch affine bindings; coefficient conversion happens outside storage locks.

use gana_core::{Affine, AlgebraError, Membership, Number, Row, Term};
use pyo3::exceptions::{PyIndexError, PyOverflowError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyInt, PyList};
use std::collections::HashSet;
use std::sync::OnceLock;

use crate::{error, members::MemberTable, NativeSelector, NumericPayload, NumericSnapshot};

type Ids = (usize, usize, usize);
type EncodedRow = (Vec<Ids>, Vec<Py<PyAny>>, Py<PyAny>);

/// Optional constraint metadata, separate from immutable coefficient storage.
#[pyclass(frozen, module = "gana._native")]
pub(crate) struct RowMembership {
    inner: Membership,
}

#[pymethods]
impl RowMembership {
    /// Export only row positions involving one stable symbolic member.
    fn rows(&self, owner: usize, member: usize) -> Vec<usize> {
        self.inner.rows(owner, member).to_vec()
    }

    /// Reserved buffer estimate; excludes allocator/hash overhead and wrappers.
    fn buffer_bytes(&self) -> usize {
        self.inner.buffer_bytes()
    }
}

/// Preserve Python integers; overflow requests the established Python compiler.
fn number(value: &Bound<'_, PyAny>) -> PyResult<Number> {
    if value.is_instance_of::<PyInt>() {
        Ok(Number::Integer(value.extract()?))
    } else {
        Ok(Number::Real(value.extract()?))
    }
}

/// Reconstruct the original number kind only when an explicit export is needed.
pub(crate) fn export_number(py: Python<'_>, value: Number) -> PyResult<Py<PyAny>> {
    match value {
        Number::Integer(value) => Ok(value.into_pyobject(py)?.into_any().unbind()),
        Number::Real(value) => Ok(value.into_pyobject(py)?.into_any().unbind()),
    }
}

/// Match legacy `-offset or 0`, including signed zero and the i128 boundary.
fn legacy_offset(py: Python<'_>, value: Number) -> PyResult<Py<PyAny>> {
    let negative = match value {
        Number::Integer(value) => match value.checked_neg() {
            Some(negative) => Number::Integer(negative),
            None => return Ok(value.into_pyobject(py)?.neg()?.unbind()),
        },
        Number::Real(0.0) => Number::Integer(0),
        Number::Real(value) => Number::Real(-value),
    };
    export_number(py, negative)
}

/// Call the active interpreter's compensated sum without a Python row loop.
fn sum_offset(
    py: Python<'_>,
    sum: &Bound<'_, PyAny>,
    batch: &Affine,
    positions: &[usize],
) -> PyResult<Number> {
    let values = positions
        .iter()
        .map(|position| {
            let row = batch.row(*position).map_err(algebra_error)?;
            legacy_offset(py, row.offset)
        })
        .collect::<PyResult<Vec<_>>>()?;
    let result = sum.call1((PyList::new(py, values)?,))?.neg()?;
    number(&result)
}

/// Keep shape/nonlinear errors distinct from the lossless-fallback signal.
pub(crate) fn algebra_error(value: AlgebraError) -> PyErr {
    match value {
        AlgebraError::Overflow => {
            PyOverflowError::new_err("affine operation requires Python numeric semantics")
        }
        AlgebraError::Shape => PyValueError::new_err("incompatible affine row counts"),
        AlgebraError::Nonlinear => PyValueError::new_err("nonlinear operation is unsupported"),
        AlgebraError::Index => PyIndexError::new_err("affine row or owner position out of range"),
    }
}

/// Decode serialized rows before publishing an immutable native batch.
fn decode_row(py: Python<'_>, data: EncodedRow) -> PyResult<Row> {
    let (ids, coefficients, offset) = data;
    if ids.len() != coefficients.len() {
        return Err(algebra_error(AlgebraError::Shape));
    }
    let terms = ids
        .into_iter()
        .zip(coefficients)
        .map(|((owner, member, column), value)| {
            Ok(Term {
                owner,
                member,
                column,
                coefficient: number(value.bind(py))?,
            })
        })
        .collect::<PyResult<_>>()?;
    Ok(Row {
        terms,
        offset: number(offset.bind(py))?,
    })
}

/// Shared immutable rows with an optional membership index for lazy metadata.
#[pyclass(frozen, module = "gana._native")]
pub(crate) struct AffineRows {
    pub(crate) inner: Affine,
    membership: OnceLock<HashSet<(usize, usize)>>,
}

impl AffineRows {
    /// Derived membership is allocated only if scalar metadata asks for it.
    fn wrap(inner: Affine) -> Self {
        Self {
            inner,
            membership: OnceLock::new(),
        }
    }

    /// Bounds-check one exported row without allocating symbolic members.
    fn row(&self, position: usize) -> PyResult<&Row> {
        self.inner.row(position).map_err(algebra_error)
    }
}

#[pymethods]
impl AffineRows {
    /// Restore detached coefficients; no Python object enters the core.
    #[new]
    fn new(py: Python<'_>, rows: Vec<EncodedRow>) -> PyResult<Self> {
        Ok(Self::wrap(Affine::new(
            rows.into_iter()
                .map(|row| decode_row(py, row))
                .collect::<PyResult<_>>()?,
        )))
    }

    /// Read a coherent native parameter batch without exporting Python scalars.
    #[staticmethod]
    fn numeric(handle: &Bound<'_, PyAny>) -> PyResult<Self> {
        let values = if let Ok(payload) = handle.extract::<PyRef<'_, NumericPayload>>() {
            payload
                .inner
                .all()
                .and_then(|snapshot| snapshot.values())
                .map_err(error)?
        } else {
            handle
                .extract::<PyRef<'_, NumericSnapshot>>()?
                .inner
                .values()
                .map_err(error)?
        };
        Ok(Self::wrap(Affine::constants(
            values.into_iter().map(Number::Real).collect(),
        )))
    }

    /// Convert staging coefficients in one call, preserving integer exactness.
    #[staticmethod]
    fn constants(py: Python<'_>, values: Vec<Py<PyAny>>) -> PyResult<Self> {
        let values = values
            .iter()
            .map(|value| number(value.bind(py)))
            .collect::<PyResult<_>>()?;
        Ok(Self::wrap(Affine::constants(values)))
    }

    /// Read selected variable IDs and solver columns without Python wrappers.
    #[staticmethod]
    fn variables(table: &MemberTable) -> PyResult<Self> {
        Ok(Self::wrap(Affine::variables(table.columns()?)))
    }

    /// Compute aligned addition, subtraction or numerical scaling in one call.
    fn combine(
        &self,
        other: &Self,
        left: Vec<usize>,
        right: Vec<usize>,
        operation: &str,
    ) -> PyResult<Self> {
        Ok(Self::wrap(
            self.inner
                .combine(&other.inner, (&left, &right), operation)
                .map_err(algebra_error)?,
        ))
    }

    /// Select rows without copying terms; nested views retain one native owner.
    fn take(&self, positions: Vec<usize>) -> PyResult<Self> {
        Ok(Self::wrap(
            self.inner.take(positions).map_err(algebra_error)?,
        ))
    }

    /// Accept a coordinate selector directly, including nested Cartesian axes.
    fn select(&self, positions: &NativeSelector) -> PyResult<Self> {
        Ok(Self::wrap(
            self.inner.select(&positions.inner).map_err(algebra_error)?,
        ))
    }

    /// Reduce all rows without transferring their positions through Python.
    fn sum_all(&self) -> PyResult<Self> {
        let positions = (0..self.inner.len()).collect();
        Ok(Self::wrap(
            self.inner.sum(&[positions]).map_err(algebra_error)?,
        ))
    }

    /// Reduce coordinate groups prepared by the frontend without scalar rows.
    fn sum_groups(&self, groups: Vec<Vec<usize>>) -> PyResult<Self> {
        Ok(Self::wrap(self.inner.sum(&groups).map_err(algebra_error)?))
    }

    /// Retain native term reduction when Python supplies compensated offsets.
    fn sum_terms(&self, groups: Option<Vec<Vec<usize>>>) -> PyResult<Self> {
        let groups = groups.unwrap_or_else(|| vec![(0..self.inner.len()).collect()]);
        Ok(Self::wrap(
            self.inner.sum_terms(&groups).map_err(algebra_error)?,
        ))
    }

    /// Preserve Python reduction semantics and concatenate terms just once.
    fn sum_python(&self, py: Python<'_>, groups: Option<Vec<Vec<usize>>>) -> PyResult<Self> {
        let groups = groups.unwrap_or_else(|| vec![(0..self.inner.len()).collect()]);
        let sum = py.import("builtins")?.getattr("sum")?;
        let offsets = groups
            .iter()
            .map(|positions| sum_offset(py, &sum, &self.inner, positions))
            .collect::<PyResult<_>>()?;
        Ok(Self::wrap(
            self.inner
                .sum_with_offsets(&groups, offsets)
                .map_err(algebra_error)?,
        ))
    }

    /// Export only offsets, avoiding variable or scalar-expression wrappers.
    fn offsets(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        self.inner
            .rows()
            .map(|row| export_number(py, row.offset))
            .collect()
    }

    /// Attach offsets computed with Python's established numeric sum policy.
    fn with_offsets(&self, py: Python<'_>, values: Vec<Py<PyAny>>) -> PyResult<Self> {
        let values = values
            .iter()
            .map(|value| number(value.bind(py)))
            .collect::<PyResult<_>>()?;
        Ok(Self::wrap(
            self.inner.with_offsets(values).map_err(algebra_error)?,
        ))
    }

    /// Expose the number of rows independently of compatibility materialization.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Export one row's coefficients when the public API requests them.
    fn coefficients(&self, py: Python<'_>, position: usize) -> PyResult<Vec<Py<PyAny>>> {
        self.row(position)?
            .terms
            .iter()
            .map(|term| export_number(py, term.coefficient))
            .collect()
    }

    /// Export column occurrences, preserving repetitions and order.
    fn columns(&self, position: usize) -> PyResult<Vec<usize>> {
        Ok(self
            .row(position)?
            .terms
            .iter()
            .map(|term| term.column)
            .collect())
    }

    /// Export the ordinary affine offset, including exact integer constants.
    fn offset(&self, py: Python<'_>, position: usize) -> PyResult<Py<PyAny>> {
        export_number(py, self.row(position)?.offset)
    }

    /// Aggregate repeated solver columns in native code with checked arithmetic.
    fn matrix(&self, py: Python<'_>, position: usize) -> PyResult<Vec<(usize, Py<PyAny>)>> {
        self.inner
            .matrix(position)
            .map_err(algebra_error)?
            .into_iter()
            .map(|(column, value)| Ok((column, export_number(py, value)?)))
            .collect()
    }

    /// Test objective membership in amortized constant time after its first read.
    fn contains(&self, owner: usize, member: usize) -> bool {
        self.membership
            .get_or_init(|| {
                self.inner
                    .rows()
                    .flat_map(|row| row.terms.iter().map(|term| (term.owner, term.member)))
                    .collect()
            })
            .contains(&(owner, member))
    }

    /// Build optional ordered membership metadata without exporting all terms.
    fn membership(&self) -> RowMembership {
        RowMembership {
            inner: Membership::new(&self.inner),
        }
    }

    /// Explicit serialization exports data, never native addresses or locks.
    fn export(&self, py: Python<'_>) -> PyResult<Vec<EncodedRow>> {
        self.inner
            .rows()
            .map(|row| {
                let ids = row
                    .terms
                    .iter()
                    .map(|term| (term.owner, term.member, term.column))
                    .collect();
                let coefficients = row
                    .terms
                    .iter()
                    .map(|term| export_number(py, term.coefficient))
                    .collect::<PyResult<_>>()?;
                Ok((ids, coefficients, export_number(py, row.offset)?))
            })
            .collect()
    }
}
