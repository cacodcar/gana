//! Coordinate tokens and symbolic records cross the boundary in batches.

use gana_core::Coordinates;
use pyo3::prelude::*;
use std::sync::Arc;

use crate::bounds::{BoundBatch, Bounds};
use crate::{error, NativeSelector};

type ExportedRecord = (Vec<usize>, usize, Option<Bounds>);

#[derive(Clone, Debug)]
struct Record {
    number: usize,
    bounds: Option<Arc<Bounds>>,
}

/// One native coordinate table, optionally carrying exact theta intervals.
#[pyclass(frozen, weakref, module = "gana._native")]
pub(crate) struct MemberTable {
    inner: Coordinates<Record>,
}

impl MemberTable {
    /// Resolve columns in native code without decoding coordinates in Python.
    pub(crate) fn columns(&self) -> PyResult<Vec<(usize, usize)>> {
        Ok(self
            .inner
            .entries()
            .map_err(error)?
            .into_iter()
            .map(|(member, record)| (member, record.number))
            .collect())
    }
}

/// Keep variable/parameter records small; only theta rows allocate endpoints.
fn records(numbers: Vec<usize>, bounds: &Bound<'_, PyAny>) -> PyResult<Vec<Record>> {
    if bounds.is_instance_of::<BoundBatch>() {
        let batch = bounds.extract::<PyRef<'_, BoundBatch>>()?;
        return shared_records(numbers, batch.rows.len(), batch.rows.iter().cloned());
    }
    let decoded: Vec<Option<Bounds>> = bounds.extract()?;
    shared_records(
        numbers,
        decoded.len(),
        decoded.into_iter().map(|pair| pair.map(Arc::new)),
    )
}

/// Share immutable endpoints while assembling records before core locks.
fn shared_records(
    numbers: Vec<usize>,
    length: usize,
    bounds: impl IntoIterator<Item = Option<Arc<Bounds>>>,
) -> PyResult<Vec<Record>> {
    if numbers.len() != length {
        return Err(error(gana_core::StorageError::Length));
    }
    Ok(numbers
        .into_iter()
        .zip(bounds)
        .map(|(number, bounds)| Record { number, bounds })
        .collect())
}

#[pymethods]
impl MemberTable {
    /// Convert all keys, IDs and endpoint strings before entering core locks.
    #[new]
    fn new(
        keys: Vec<Vec<usize>>,
        numbers: Vec<usize>,
        bounds: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: Coordinates::new(keys, records(numbers, bounds)?).map_err(error)?,
        })
    }

    /// Create compact coordinates from unique axis tokens in row-major order.
    #[staticmethod]
    fn cartesian(
        axes: Vec<Vec<usize>>,
        numbers: Vec<usize>,
        bounds: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: Coordinates::cartesian(axes, records(numbers, bounds)?).map_err(error)?,
        })
    }

    /// Append coordinates and records atomically, preserving all earlier IDs.
    fn append(
        &self,
        keys: Vec<Vec<usize>>,
        numbers: Vec<usize>,
        bounds: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        self.inner
            .append(keys, records(numbers, bounds)?)
            .map_err(error)
    }

    /// Number of members; root handles grow while selections remain fixed.
    fn __len__(&self) -> PyResult<usize> {
        self.inner.len().map_err(error)
    }

    /// Read the stable local owner ID without materializing a scalar wrapper.
    fn id(&self, position: usize) -> PyResult<usize> {
        self.inner.id(position).map_err(error)
    }

    /// Return one detached coordinate-token tuple.
    fn key(&self, position: usize) -> PyResult<Vec<usize>> {
        self.inner.key(position).map_err(error)
    }

    /// Resolve a coordinate to its position in this view.
    fn lookup(&self, key: Vec<usize>) -> PyResult<usize> {
        self.inner.lookup(&key).map_err(error)
    }

    /// Resolve a complete Python-converted key batch with one core read lock.
    fn lookup_many(&self, keys: Vec<Vec<usize>>) -> PyResult<Vec<usize>> {
        self.inner.lookup_many(&keys).map_err(error)
    }

    /// Select local positions, compacting regular progressions in native code.
    fn take(&self, positions: Vec<usize>) -> PyResult<Self> {
        Ok(Self {
            inner: self.inner.take(positions).map_err(error)?,
        })
    }

    /// Resolve axes directly; return matching source-local numeric membership.
    #[pyo3(signature = (axes, *, last=false))]
    fn product(&self, axes: Vec<Vec<usize>>, last: bool) -> PyResult<(Self, NativeSelector)> {
        let (inner, selector) = self.inner.product_for(axes, last).map_err(error)?;
        Ok((Self { inner }, NativeSelector { inner: selector }))
    }

    /// Capture fixed full membership in O(1), sharing all coordinate records.
    fn freeze(&self) -> PyResult<Self> {
        Ok(Self {
            inner: self.inner.freeze().map_err(error)?,
        })
    }

    /// Return a member's global model column number.
    fn number(&self, position: usize) -> PyResult<usize> {
        Ok(self.inner.get(position).map_err(error)?.number)
    }

    /// Export exact endpoint encodings; Python reconstructs integers after unlock.
    fn bounds(&self, position: usize) -> PyResult<Option<Bounds>> {
        Ok(self
            .inner
            .get(position)
            .map_err(error)?
            .bounds
            .map(|value| (*value).clone()))
    }

    /// Replace an already validated interval while keeping its column number.
    fn set_bounds(&self, position: usize, bounds: Bounds) -> PyResult<()> {
        let mut record = self.inner.get(position).map_err(error)?;
        record.bounds = Some(Arc::new(bounds));
        self.inner.set(position, record).map_err(error)
    }

    /// Export intervals in one coherent batch, before Python number reconstruction.
    fn all_bounds(&self) -> PyResult<Vec<Option<Bounds>>> {
        Ok(self
            .inner
            .values()
            .map_err(error)?
            .into_iter()
            .map(|record| record.bounds.map(|pair| (*pair).clone()))
            .collect())
    }

    /// Serialize detached table contents; never serialize locks or addresses.
    fn export(&self) -> PyResult<Vec<ExportedRecord>> {
        (0..self.__len__()?)
            .map(|position| {
                Ok((
                    self.key(position)?,
                    self.number(position)?,
                    self.bounds(position)?,
                ))
            })
            .collect()
    }
}
