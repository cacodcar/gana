//! Batch theta validation and encoding, before any native owner is mutated.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyFloat, PyInt, PyList, PyString, PyTuple};
use std::sync::Arc;

/// Decimal text preserves arbitrary integers; empty text denotes a float.
pub(crate) type Endpoint = (String, f64);
pub(crate) type Bounds = (Endpoint, Endpoint);

/// Short-lived, immutable native intervals prepared before coordinate mutation.
#[pyclass(frozen, module = "gana._native")]
pub(crate) struct BoundBatch {
    pub(crate) rows: Vec<Option<Arc<Bounds>>>,
}

type Pair<'py> = (Bound<'py, PyAny>, Bound<'py, PyAny>);

/// Restrict shortcuts to built-ins; subclasses retain their Python hooks.
fn primitive(value: &Bound<'_, PyAny>) -> bool {
    value.is_exact_instance_of::<PyInt>() || value.is_exact_instance_of::<PyFloat>()
}

/// Recognize an ordinary pair without invoking user-defined conversion code.
fn primitive_pair<'py>(value: &Bound<'py, PyAny>) -> PyResult<Option<Pair<'py>>> {
    if !value.is_exact_instance_of::<PyTuple>() {
        return Ok(None);
    }
    let pair = value.cast::<PyTuple>()?;
    if pair.len() != 2 {
        return Ok(None);
    }
    let lower = pair.get_item(0)?;
    let upper = pair.get_item(1)?;
    Ok((primitive(&lower) && primitive(&upper)).then_some((lower, upper)))
}

/// Match math.isnan's conversion/overflow order, then compare exact numbers.
fn validate_pair(lower: &Bound<'_, PyAny>, upper: &Bound<'_, PyAny>) -> PyResult<()> {
    // Comparing extracted doubles would round large integers before ordering.
    if lower.extract::<f64>()?.is_nan() || upper.extract::<f64>()?.is_nan() || lower.gt(upper)? {
        return Err(PyValueError::new_err(
            "Theta bounds must be ordered and cannot contain NaN",
        ));
    }
    Ok(())
}

/// Return a fresh accepted list; no validation survives later staging edits.
#[pyfunction]
pub(crate) fn validate_bounds<'py>(
    values: &Bound<'py, PyAny>,
    fallback: &Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyList>> {
    let result = PyList::empty(values.py());
    for value in values.try_iter()? {
        let value = value?;
        if let Some((lower, upper)) = primitive_pair(&value)? {
            validate_pair(&lower, &upper)?;
            result.append(value)?;
        } else {
            result.append(fallback.call1((value,))?)?;
        }
    }
    Ok(result)
}

/// Preserve exact integer text and reuse floating endpoints without conversion.
fn encode_endpoint<'py>(
    value: Bound<'py, PyAny>,
    empty: &Bound<'py, PyAny>,
    zero: &Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyTuple>> {
    let fields = if value.is_exact_instance_of::<PyInt>() {
        [value.str()?.into_any(), zero.clone()]
    } else {
        [empty.clone(), value]
    };
    PyTuple::new(empty.py(), fields)
}

/// Construct one pair with shared marker objects and no integer rounding.
fn encode_pair<'py>(
    lower: Bound<'py, PyAny>,
    upper: Bound<'py, PyAny>,
    empty: &Bound<'py, PyAny>,
    zero: &Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyTuple>> {
    PyTuple::new(
        empty.py(),
        [
            encode_endpoint(lower, empty, zero)?,
            encode_endpoint(upper, empty, zero)?,
        ],
    )
}

/// Encode a validated batch before locks; fallback conversion stays row-ordered.
#[pyfunction]
pub(crate) fn encode_bounds<'py>(
    values: &Bound<'py, PyAny>,
    fallback: &Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyList>> {
    let py = values.py();
    let result = PyList::empty(py);
    let empty = PyString::new(py, "").into_any();
    let zero = PyFloat::new(py, 0.0).into_any();
    for value in values.try_iter()? {
        let value = value?;
        if let Some((lower, upper)) = primitive_pair(&value)? {
            result.append(encode_pair(lower, upper, &empty, &zero)?)?;
        } else {
            result.append(fallback.call1((value,))?)?;
        }
    }
    Ok(result)
}

/// Decode built-in endpoints directly without creating Python marker tuples.
fn native_endpoint(value: &Bound<'_, PyAny>) -> PyResult<Endpoint> {
    if value.is_exact_instance_of::<PyInt>() {
        Ok((value.str()?.extract()?, 0.0))
    } else {
        Ok((String::new(), value.extract()?))
    }
}

/// Recognize and decode an immutable built-in interval without Python hooks.
fn primitive_bounds(value: &Bound<'_, PyAny>) -> PyResult<Option<Bounds>> {
    if let Some((lower, upper)) = primitive_pair(value)? {
        return Ok(Some((native_endpoint(&lower)?, native_endpoint(&upper)?)));
    }
    Ok(None)
}

/// Keep uncommon conversions in their original Python order, outside locks.
fn native_pair(value: &Bound<'_, PyAny>, fallback: &Bound<'_, PyAny>) -> PyResult<Option<Bounds>> {
    if let Some(bounds) = primitive_bounds(value)? {
        return Ok(Some(bounds));
    }
    fallback.call1((value,))?.extract()
}

/// Share consecutive identical built-in pairs in an ordinary staging list.
fn prepare_list(values: &Bound<'_, PyList>, fallback: &Bound<'_, PyAny>) -> PyResult<BoundBatch> {
    let mut rows: Vec<Option<Arc<Bounds>>> = Vec::with_capacity(values.len());
    let mut previous: Option<Bound<'_, PyAny>> = None;
    // Use Python iteration so fallback edits can extend or shorten the list.
    for value in values.as_any().try_iter()? {
        let value = value?;
        // The previous native interval already lives in rows. Borrow it here
        // and increment its reference count only for an actual repeated row.
        if let (Some(source), Some(bounds)) = (&previous, rows.last()) {
            if source.is(&value) {
                rows.push(bounds.clone());
                continue;
            }
        }
        // Hold the tuple itself, not a pointer that could be recycled. Only
        // immutable built-in endpoints qualify; callbacks always run per row.
        previous = None;
        if let Some(bounds) = primitive_bounds(&value)? {
            rows.push(Some(Arc::new(bounds)));
            previous = Some(value);
        } else {
            rows.push(
                fallback
                    .call1((value,))?
                    .extract::<Option<Bounds>>()?
                    .map(Arc::new),
            );
        }
    }
    Ok(BoundBatch { rows })
}

/// Prepare detached intervals with bounded, batch-local sharing metadata.
#[pyfunction]
pub(crate) fn prepare_bounds(
    values: &Bound<'_, PyAny>,
    fallback: &Bound<'_, PyAny>,
) -> PyResult<BoundBatch> {
    // Arbitrary iterators may change integer conversion settings between rows.
    // A callback clears list reuse, preserving those same conversion effects.
    if values.is_exact_instance_of::<PyList>() {
        return prepare_list(values.cast::<PyList>()?, fallback);
    }
    let mut rows = Vec::new();
    for value in values.try_iter()? {
        rows.push(native_pair(&value?, fallback)?.map(Arc::new));
    }
    Ok(BoundBatch { rows })
}
