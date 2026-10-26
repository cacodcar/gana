"""Numeric interoperability shared by parameters and symbolic expressions."""

from __future__ import annotations

from typing import ClassVar, NoReturn

import numpy as np


def normalize_operand(value):
    """Convert real NumPy values, preserving axes and interval tuples.

    Tuples retain Gana's interval convention. Numeric arrays must be scalar or
    one dimensional; callers select explicit model axes before using a vector.
    Unknown objects are left to the operator's ordinary type dispatch.
    """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, np.ndarray):
        if value.ndim > 1:
            message = (
                "Numeric operands require a scalar or one-dimensional array"
            )
            raise ValueError(message)
        value = value.tolist()
    if isinstance(value, np.generic):
        if value.dtype.kind not in "biuf":
            message = "Numeric operands must be real"
            raise TypeError(message)
        value = float(value) if value.dtype.kind == "f" else int(value)
    if isinstance(value, list):
        return _normalize_list(value)
    return value


def _normalize_list(values):
    """
    Validate a nonempty homogeneous vector before arithmetic can short-cut.
    """
    if not values:
        message = "Arithmetic requires a nonempty numeric list"
        raise TypeError(message)
    if all(isinstance(v, (int, float)) for v in values):
        return values
    result = [normalize_operand(v) for v in values]
    if all(isinstance(v, (int, float)) for v in result):
        return result
    if all(isinstance(v, tuple) for v in result):
        return result
    message = "Arithmetic requires real numbers or a list of interval tuples"
    raise TypeError(message)


class NumericDispatch:
    """Let NumPy call Gana operators instead of traversing symbolic members."""

    __array_priority__ = 1000
    _numpy_binary: ClassVar = {
        "add": ("__add__", "__radd__"),
        "subtract": ("__sub__", "__rsub__"),
        "multiply": ("__mul__", "__rmul__"),
        "divide": ("__truediv__", "__rtruediv__"),
        "true_divide": ("__truediv__", "__rtruediv__"),
        "floor_divide": ("__floordiv__", "__rfloordiv__"),
        "remainder": ("__mod__", "__rmod__"),
        "power": ("__pow__", "__rpow__"),
        "equal": ("__eq__", "__eq__"),
        "not_equal": ("__ne__", "__ne__"),
        "less": ("__lt__", "__gt__"),
        "less_equal": ("__le__", "__ge__"),
        "greater": ("__gt__", "__lt__"),
        "greater_equal": ("__ge__", "__le__"),
    }
    _numpy_unary: ClassVar = {
        "negative": "__neg__",
        "positive": "__pos__",
        "absolute": "__abs__",
    }

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        """
        Dispatch supported elementwise calls, rejecting out/reduce semantics.
        """
        if method != "__call__" or kwargs:
            return NotImplemented
        name = ufunc.__name__
        if len(inputs) == 1 and name in self._numpy_unary:
            operation = getattr(self, self._numpy_unary[name], None)
            return NotImplemented if operation is None else operation()
        binary_arity = 2
        if len(inputs) != binary_arity or name not in self._numpy_binary:
            return NotImplemented
        reverse = inputs[1] is self
        operation = getattr(self, self._numpy_binary[name][reverse], None)
        if operation is None:
            return NotImplemented
        return operation(normalize_operand(inputs[not reverse]))


def reject_disequality() -> NoReturn:
    """A symbolic disequality is a disjunction, outside the affine contract."""
    message = (
        "Symbolic != is unsupported; use ==, <= or >= to form a constraint"
    )
    raise TypeError(message)
