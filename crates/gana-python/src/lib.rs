//! PyO3 boundary: input extraction completes before acquiring core locks.

use gana_core::{Owner, Payload, Selector, Snapshot, StorageError};
use pyo3::exceptions::{PyIndexError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
mod affine;
mod bounds;
mod members;
mod sparse;

/// Opaque validated local membership shared by coordinates and numeric snapshots.
#[pyclass(frozen, module = "gana._native")]
struct NativeSelector {
    inner: Selector,
}

#[pymethods]
impl NativeSelector {
    /// Resolve one local occurrence without exporting or expanding the selector.
    fn at(&self, position: usize) -> PyResult<usize> {
        self.inner.at(position).map_err(error)
    }

    /// Find the last selected occurrence, matching shared expression row numbering.
    fn last(&self, member: usize) -> Option<usize> {
        self.inner.position_for(member, true)
    }
}

/// Translate recoverable native failures into ordinary Python exceptions.
fn error(value: StorageError) -> PyErr {
    match value {
        StorageError::Index => PyIndexError::new_err("storage position out of range"),
        StorageError::Length => PyValueError::new_err("update lengths differ"),
        StorageError::Poisoned => PyRuntimeError::new_err("storage lock poisoned"),
        StorageError::VersionOverflow => PyRuntimeError::new_err("storage version exhausted"),
    }
}

/// Stable root identity; replacement detaches previously retained payloads.
#[pyclass(frozen, weakref, module = "gana._native")]
struct NumericOwner {
    inner: Owner<f64>,
}

#[pymethods]
impl NumericOwner {
    /// Convert all input numbers before constructing native storage.
    #[new]
    fn new(values: Vec<f64>) -> Self {
        Self {
            inner: Owner::new(values),
        }
    }
    /// Return a shared payload handle without copying values.
    fn payload(&self) -> PyResult<NumericPayload> {
        Ok(NumericPayload {
            inner: self.inner.payload().map_err(error)?,
        })
    }
    /// Input conversion precedes atomic root replacement.
    fn replace(&self, values: Vec<f64>) -> PyResult<()> {
        self.inner.replace(values).map_err(error)
    }
}

/// Independently retained mutable payload with immutable snapshots.
#[pyclass(frozen, weakref, module = "gana._native")]
struct NumericPayload {
    inner: Payload<f64>,
}

#[pymethods]
impl NumericPayload {
    /// Pin a value version using an already validated coordinate selection.
    fn select(&self, selector: &NativeSelector) -> PyResult<NumericSnapshot> {
        Ok(NumericSnapshot {
            inner: self.inner.snapshot(selector.inner.clone()).map_err(error)?,
        })
    }
    /// Convert all input numbers before constructing native storage.
    #[new]
    fn new(values: Vec<f64>) -> Self {
        Self {
            inner: Payload::new(values),
        }
    }
    /// Batch export is detached; no writable native buffers escape.
    fn values(&self) -> PyResult<Vec<f64>> {
        self.inner.all().and_then(|s| s.values()).map_err(error)
    }
    /// Return membership length without exporting Python numbers.
    fn __len__(&self) -> PyResult<usize> {
        Ok(self.inner.all().map_err(error)?.len())
    }
    /// Read a position from one coherent data version.
    fn get(&self, position: usize) -> PyResult<f64> {
        self.inner
            .all()
            .and_then(|s| s.get(position))
            .map_err(error)
    }
    /// Validate positions before one copy-on-write update.
    fn set_many(&self, positions: Vec<usize>, values: Vec<f64>) -> PyResult<()> {
        self.inner.set_many(&positions, values).map_err(error)
    }
    /// Append an already converted batch while preserving existing IDs.
    fn append(&self, values: Vec<f64>) -> PyResult<()> {
        self.inner.append(values).map_err(error)
    }
    /// Pin an immutable version and compact regular membership.
    fn span(&self, start: usize, step: isize, len: usize) -> PyResult<NumericSnapshot> {
        let bound = self.__len__()?;
        let selector = Selector::span(start, step, len, bound).map_err(error)?;
        Ok(NumericSnapshot {
            inner: self.inner.snapshot(selector).map_err(error)?,
        })
    }
    /// Pin irregular membership, retaining order and duplicate IDs.
    fn take(&self, positions: Vec<usize>) -> PyResult<NumericSnapshot> {
        let selector = Selector::compact(positions, self.__len__()?).map_err(error)?;
        Ok(NumericSnapshot {
            inner: self.inner.snapshot(selector).map_err(error)?,
        })
    }
    /// Report the retained payload version.
    #[getter]
    fn version(&self) -> PyResult<u64> {
        Ok(self.inner.all().map_err(error)?.version())
    }
    /// Report vector capacity in bytes, excluding handle bookkeeping.
    #[getter]
    fn reserved_bytes(&self) -> PyResult<usize> {
        Ok(self.inner.all().map_err(error)?.reserved_bytes())
    }
}

/// Immutable native snapshot, independent of its original root's lifetime.
#[pyclass(frozen, weakref, module = "gana._native")]
struct NumericSnapshot {
    inner: Snapshot<f64>,
}

#[pymethods]
impl NumericSnapshot {
    /// Compose compact membership without exporting IDs through Python.
    fn select(&self, selector: &NativeSelector) -> PyResult<Self> {
        Ok(Self {
            inner: self.inner.select(&selector.inner).map_err(error)?,
        })
    }
    /// Compose a nested selection while retaining the same data version.
    fn take(&self, positions: Vec<usize>) -> PyResult<Self> {
        Ok(Self {
            inner: self.inner.take(positions).map_err(error)?,
        })
    }
    /// Materialize a detached Python-compatible numeric batch.
    fn values(&self) -> PyResult<Vec<f64>> {
        self.inner.values().map_err(error)
    }
    /// Read a position from one coherent data version.
    fn get(&self, position: usize) -> PyResult<f64> {
        self.inner.get(position).map_err(error)
    }
    /// Return membership length without exporting Python numbers.
    fn __len__(&self) -> usize {
        self.inner.len()
    }
    /// Report the retained payload version.
    #[getter]
    fn version(&self) -> u64 {
        self.inner.version()
    }
    /// Report vector capacity in bytes, excluding handle bookkeeping.
    #[getter]
    fn reserved_bytes(&self) -> usize {
        self.inner.reserved_bytes()
    }
}

/// Register the coordinate and numeric owners shared by expression bindings.
fn register_owners(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<bounds::BoundBatch>()?;
    module.add_class::<members::MemberTable>()?;
    module.add_class::<NativeSelector>()?;
    module.add_class::<NumericOwner>()?;
    module.add_class::<NumericPayload>()?;
    module.add_class::<NumericSnapshot>()?;
    Ok(())
}

/// Keep bound conversion entry points separate from owner registration.
fn register_bounds(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(bounds::validate_bounds, module)?)?;
    module.add_function(wrap_pyfunction!(bounds::encode_bounds, module)?)?;
    module.add_function(wrap_pyfunction!(bounds::prepare_bounds, module)?)?;
    Ok(())
}

/// Export explicit native types; missing extensions never masquerade as Rust.
#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    register_bounds(module)?;
    module.add_class::<affine::AffineRows>()?;
    module.add_class::<affine::RowMembership>()?;
    module.add_class::<sparse::SparseRows>()?;
    register_owners(module)?;
    module.add("BACKEND", "rust-owners-v1")?;
    Ok(())
}
