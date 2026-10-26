"""Comparison protocol and numeric compatibility at the parameter boundary."""

import operator
from unittest import TestCase

import numpy as np
import pytest

from src.gana import I, P, Prg, V

CHECK = TestCase()
OPERATIONS = [
    operator.eq,
    operator.ne,
    operator.lt,
    operator.le,
    operator.gt,
    operator.ge,
]
REFLECTED = {
    "eq": "eq",
    "ne": "ne",
    "lt": "gt",
    "le": "ge",
    "gt": "lt",
    "ge": "le",
}


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("values", [2, [1, 2]])
def test_unsupported_dunder_defers(operation, values):
    """
    Unknown operand types must reach Python's reflected-operation dispatch.
    """
    parameter = P(_=values)
    method = getattr(parameter, f"__{operation.__name__}__")
    for other in (None, object(), (1, 2), {1: 2}, "value", 1j):
        CHECK.assertIs(method(other), NotImplemented)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_unknown_public_comparison(operation):
    """
    Identity fallback handles equality; unsupported ordering raises TypeError.
    """
    parameter = P(_=2)
    for left, right in ((parameter, object()), (object(), parameter)):
        if operation in (operator.eq, operator.ne):
            CHECK.assertIs(operation(left, right), (operation is operator.ne))
        else:
            with pytest.raises(TypeError):
                operation(left, right)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_reflected_result_is_preserved(operation):
    """
    Dispatch once, pass the original operand, and retain non-boolean results.
    """
    parameter = P(_=2)
    calls = []
    sentinel = object()

    def reflect(self, other):
        """Record the protocol callback without using symbolic equality."""
        calls.append((self, other))
        return sentinel

    name = f"__{REFLECTED[operation.__name__]}__"
    foreign = type("Foreign", (), {name: reflect})()
    CHECK.assertIs(operation(parameter, foreign), sentinel)
    CHECK.assertEqual(len(calls), 1)
    CHECK.assertIs(calls[0][0], foreign)
    CHECK.assertIs(calls[0][1], parameter)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_reflected_exception_propagates(operation):
    """Do not stringify a foreign operand or swallow errors in its handler."""

    def reflect(_self, _other):
        """Expose the exact exception from the selected reflected method."""
        message = "reflected failure"
        raise LookupError(message)

    def render(_self):
        """Fail if the unsupported-type path tries to render the operand."""
        message = "unexpected rendering"
        raise RuntimeError(message)

    name = f"__{REFLECTED[operation.__name__]}__"
    foreign = type("Foreign", (), {name: reflect, "__str__": render})()
    with pytest.raises(LookupError, match="reflected failure"):
        operation(P(_=2), foreign)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_scalar_numeric_compatibility(operation):
    """
    Scalar numeric and parameter comparisons retain ordinary numeric results.
    """
    for value in (-3, 0, 2):
        parameter = P(_=value)
        for other in (-4, 0, 2, 5):
            CHECK.assertIs(
                operation(parameter, other),
                operation(value, other),
            )
            CHECK.assertIs(
                operation(parameter, P(_=other)),
                operation(value, other),
            )


@pytest.mark.parametrize("operation", OPERATIONS)
def test_sequence_compatibility(operation):
    """
    Preserve pairwise-all, including !=, and the existing zip truncation
    policy.
    """
    parameter = P(_=[1, 2])
    for values in ([1, 2], [1, 3], [3, 4]):
        expected = all(operation(a, b) for a, b in zip([1, 2], values))
        CHECK.assertIs(operation(parameter, values), expected)
        CHECK.assertIs(operation(parameter, P(_=values)), expected)
    for other in ([1], P(_=[1])):
        with pytest.warns(UserWarning, match="Index mismatch"):
            CHECK.assertIs(operation(parameter, other), operation(1, 1))
    for other in ([1, 2], parameter):
        with pytest.raises(
            NotImplementedError,
            match="cannot compare a number",
        ):
            operation(P(_=2), other)


@pytest.mark.parametrize(
    "operation",
    [operator.lt, operator.le, operator.gt, operator.ge],
)
def test_set_zero_sign_shortcuts(operation):
    """
    Zero comparisons use the existing set sign case, including negated sets.
    """
    parameter = P(_=[1, 2])
    CHECK.assertIs(operation(parameter, 0), operation(1, 0))
    CHECK.assertIs(operation(-parameter, 0), operation(-1, 0))


@pytest.mark.parametrize(
    "operation",
    [operator.eq, operator.lt, operator.le, operator.gt, operator.ge],
)
@pytest.mark.parametrize("affine", [False, True])
def test_reflected_symbolic_constraint(operation, affine):
    """
    Parameter-left comparisons retain the exact reflected row and RHS values.
    """
    p = Prg()
    p.i = I(size=2)
    p.x = V(p.i)
    p.limit = P(p.i, _=[5, 7])
    expression = 2 * p.x + 3 if affine else p.x
    p.c = operation(p.limit, expression)
    coefficient, offset = (2, 3) if affine else (1, 0)
    sign = -1 if operation in (operator.lt, operator.le) else 1
    np.testing.assert_array_equal(p.A, sign * coefficient * np.eye(2))
    np.testing.assert_array_equal(
        np.asarray(p.B).reshape(-1),
        sign * (np.array([5, 7]) - offset),
    )
