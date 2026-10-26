//! Exact sparse export and explicitly requested dense Python compatibility.

use crate::affine::{algebra_error, export_number, AffineRows};
use crate::members::MemberTable;
use gana_core::{Number, Sparse};
use pyo3::prelude::*;
use pyo3::types::{PyList, PySequenceMethods};

type Parts = (Vec<Py<PyAny>>, Vec<usize>, Vec<usize>);
type Tables<'py> = Vec<Vec<Option<PyRef<'py, MemberTable>>>>;
type ColumnMaps = Vec<Vec<Option<Vec<usize>>>>;

/// Read late-bound columns inside Rust; no Python scalar members are needed.
fn column_maps(tables: Tables<'_>) -> PyResult<ColumnMaps> {
    tables
        .into_iter()
        .map(|owners| owners.into_iter().map(owner_columns).collect())
        .collect()
}

/// Table order corresponds to the anonymous owner's captured member IDs.
fn owner_columns(table: Option<PyRef<'_, MemberTable>>) -> PyResult<Option<Vec<usize>>> {
    table
        .map(|table| {
            Ok(table
                .columns()?
                .into_iter()
                .map(|(_, column)| column)
                .collect())
        })
        .transpose()
}

/// A detached immutable compilation; Python exports cannot mutate its buffers.
#[pyclass(frozen, module = "gana._native")]
pub(crate) struct SparseRows {
    inner: Sparse,
}

#[pymethods]
impl SparseRows {
    /// Compile already ordered batches without exporting term occurrences.
    #[new]
    #[pyo3(signature = (batches, columns, *, owners=None, negate=false, column_tables=None))]
    fn new(
        batches: Vec<PyRef<'_, AffineRows>>,
        columns: usize,
        owners: Option<Vec<Vec<bool>>>,
        negate: bool,
        column_tables: Option<Tables<'_>>,
    ) -> PyResult<Self> {
        let inputs = batches.iter().map(|batch| &batch.inner).collect::<Vec<_>>();
        let factor = Number::Integer(if negate { -1 } else { 1 });
        let mappings = column_tables.map(column_maps).transpose()?;
        Ok(Self {
            inner: Sparse::compile_mapped(
                &inputs,
                columns,
                owners.as_deref(),
                factor,
                mappings.as_ref(),
            )
            .map_err(algebra_error)?,
        })
    }

    /// Return exact coefficient values and detached CSR index buffers.
    fn parts(&self, py: Python<'_>) -> PyResult<Parts> {
        Ok((
            self.inner
                .data
                .iter()
                .map(|value| export_number(py, *value))
                .collect::<PyResult<_>>()?,
            self.inner.indices.clone(),
            self.inner.indptr.clone(),
        ))
    }

    /// Allocate detached Python rows directly, preserving exact number kinds.
    ///
    /// List repetition fills zero slots inside Python without a Rust object
    /// vector and a second per-cell conversion. Repeat once per row so mutable
    /// rows never alias; only immutable integer zeros are shared.
    fn dense<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let zero = PyList::new(py, [0_i64])?;
        let result = PyList::empty(py);
        for span in self.inner.indptr.windows(2) {
            let row = zero
                .as_sequence()
                .repeat(self.inner.columns)?
                .cast_into::<PyList>()?;
            for position in span[0]..span[1] {
                row.set_item(
                    self.inner.indices[position],
                    export_number(py, self.inner.data[position])?,
                )?;
            }
            result.append(row)?;
        }
        Ok(result)
    }

    /// Return bounds in the same row order and number kinds as the dense API.
    fn rhs(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        self.inner
            .rhs
            .iter()
            .map(|value| export_number(py, *value))
            .collect()
    }

    /// Include unused variable columns and empty constraint sets in the shape.
    #[getter]
    fn shape(&self) -> (usize, usize) {
        (self.inner.rhs.len(), self.inner.columns)
    }

    /// Native vector capacities only; not total model or process memory.
    #[getter]
    fn reserved_bytes(&self) -> usize {
        self.inner.reserved_bytes()
    }
}
