"""
Independent algebraic oracles for expression closure and numeric dispatch.
"""

import operator
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf, sigma
from gana.sets.constraint import C
from gana.sets.function import F

CHECK = TestCase()
ROW_BOUND = 20
PARTIAL_BOUND = 30


def model(size=3):
    """Create distinct variable and theta columns on a common domain."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i, nn=False)
    p.t = T(p.i, _=[(n, n + 5) for n in range(size)])
    return p


@pytest.mark.parametrize(
    "coefficient",
    [2, np.int64(2), np.float32(2), np.array([2, 2, 2])],
)
def test_direct_numeric_function(coefficient):
    """
    The public F constructor accepts the numeric types its dunders accept.
    """
    p = model()
    p.row = F(one=coefficient, two=p.x, mul=True) + 3 <= ROW_BOUND
    np.testing.assert_array_equal(p.A, 2 * np.eye(3))
    np.testing.assert_array_equal(p.B, [17] * 3)


@pytest.mark.parametrize("shape", ["root", "selection", "member"])
@pytest.mark.parametrize(
    "build, coefficient, constant",
    [
        (lambda t: t + 2, 1, 2),
        (lambda t: t + t, 2, 0),
        (lambda t: 2 * (t + 0) + 3, 2, 3),
        (lambda t: (3 * (t + 0) - 4) / 2, 1.5, -2),
        (lambda t: 2 * (t + 3) - t, 1, 6),
        (lambda t: -(t + 2), -1, -2),
        (lambda t: t - t, 0, 0),
    ],
)
def test_theta_expression_closure(shape, build, coefficient, constant):
    """Nested operations retain coefficients on the original theta columns."""
    p = model()
    x, t, columns = p.x, p.t, [0, 1, 2]
    if shape == "selection":
        x, t, columns = p.x(p.i[::-2]), p.t(p.i[::-2]), [2, 0]
    elif shape == "member":
        x, t, columns = p.x[1], p.t[1], [1]
    original = tuple(p.thetas)
    p.row = x <= build(t)
    np.testing.assert_array_equal(p.A, np.eye(3)[columns])
    np.testing.assert_array_equal(p.B, [constant] * len(columns))
    np.testing.assert_array_equal(p.F, coefficient * np.eye(3)[columns])
    CHECK.assertEqual(p.n_thetas, 3)
    CHECK.assertTrue(all(a is b for a, b in zip(original, p.thetas)))
    CHECK.assertEqual(p.t._validated_bounds(), [(0, 5), (1, 6), (2, 7)])


def test_transformed_theta_is_reused_across_constraints():
    """A transformed interval has a new column, reused by subsequent rows."""
    p = model(1)
    scaled = 2 * p.t
    p.first = p.x <= p.t
    p.second = p.x <= scaled
    p.third = p.x >= scaled
    np.testing.assert_array_equal(p.F, [[1, 0], [0, 1], [0, -1]])
    CHECK.assertEqual(p.n_thetas, 2)
    CHECK.assertIs(p.theta_sets[1], scaled)
    CHECK.assertEqual(scaled._validated_bounds(), [(0, 10)])


def test_anonymous_selected_theta_owner():
    """
    Selections of an anonymous owner resolve once, including unused members.
    """
    p = model()
    anonymous = T(p.i, _=(1, 4))
    p.row = p.x(p.i[::-2]) <= 2 * (anonymous(p.i[::-2]) + 0) + 1
    np.testing.assert_array_equal(
        p.F,
        [[0, 0, 0, 0, 0, 2], [0, 0, 0, 2, 0, 0]],
    )
    CHECK.assertEqual(p.n_theta_sets, 2)
    CHECK.assertTrue(all(t.parent is anonymous for t in p.thetas[3:]))


def test_anonymous_expression_member_reuses_owner():
    """Arithmetic on an unregistered F member must not create new intervals."""
    p = model()
    anonymous = T(p.i, _=(1, 4))
    expression = 2 * (anonymous + 0) + 3
    p.row = p.x[0] <= -(expression[1] / 2)
    np.testing.assert_array_equal(p.F, [[0, 0, 0, 0, -1, 0]])
    np.testing.assert_array_equal(p.B, [-1.5])
    CHECK.assertEqual(p.n_theta_sets, 2)
    CHECK.assertTrue(all(t.parent is anonymous for t in p.thetas[3:]))


@pytest.mark.parametrize("dtype", [np.int64, np.float32, np.float64])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("relation", [operator.eq, operator.le, operator.ge])
def test_numpy_symbolic_comparisons(dtype, reverse, relation):
    """
    NumPy comparisons return C objects instead of coercing them to booleans.
    """
    p = model()
    expression = 2 * p.x + 3
    result = (
        relation(dtype(5), expression)
        if reverse
        else relation(expression, dtype(5))
    )
    CHECK.assertIsInstance(result, C)
    p.row = result
    negative = (relation is operator.ge) != reverse
    sign = -1 if negative and relation is not operator.eq else 1
    np.testing.assert_array_equal(p.A, 2 * sign * np.eye(3))
    np.testing.assert_array_equal(p.B, [2 * sign] * 3)


@pytest.mark.parametrize(
    "denominator",
    [np.int64(2), np.float32(2), np.array(2), np.array([2, 4, 8])],
)
def test_numpy_division(denominator):
    """Scalar, zero-dimensional and vector denominators retain constants."""
    p = model()
    p.row = (2 * p.x + 3) / denominator <= ROW_BOUND
    values = np.full(3, 2) if np.ndim(denominator) == 0 else denominator
    np.testing.assert_array_equal(p.A, np.diag(2 / values))
    np.testing.assert_array_equal(p.B, 20 - 3 / values)


@pytest.mark.parametrize(
    "operation",
    [operator.truediv, operator.floordiv, operator.mod],
)
def test_reflected_zero_denominator(operation):
    """Reflected zero numerators cannot hide a zero denominator."""
    with pytest.raises(ZeroDivisionError):
        operation(np.int64(0), P(_=[1, 0, 2]))


def test_reduction_axis_validation():
    """
    Reject unrelated axes, inconsistent positions and implicit objectives.
    """
    p = model()
    p.j = I(size=3)
    expression = 2 * p.x + 3
    with pytest.raises(ValueError, match="exactly one"):
        sigma(expression, p.j)
    with pytest.raises(ValueError, match="position"):
        sigma(expression, p.i, position=1)
    with pytest.raises(ValueError, match="position"):
        sigma(expression, position=0)
    with pytest.raises(ValueError, match="scalar"):
        inf(expression)


def test_variable_short_sum_remaining_axis():
    """The two-term optimization retains only the nonsummed output axis."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=3)
    p.x = V(p.i, p.j)
    reduced = sigma(p.x, p.i)
    p.row = (2 * reduced + 3)(p.j[::-1]) <= ROW_BOUND
    np.testing.assert_array_equal(
        p.A,
        [[0, 0, 2, 0, 0, 2], [0, 2, 0, 0, 2, 0], [2, 0, 0, 2, 0, 0]],
    )
    np.testing.assert_array_equal(p.B, [17] * 3)


@pytest.mark.parametrize(
    "relation, sign, leq",
    [
        (operator.le, -1, True),
        (operator.ge, 1, True),
        (operator.eq, -1, False),
    ],
)
def test_theta_only_constraints(relation, sign, leq):
    """
    Pure theta constraints are symbolic rows, with correct RHS orientation.
    """
    p = model()
    constraint = relation(p.t, 2)
    CHECK.assertIsInstance(constraint, C)
    p.row = constraint
    np.testing.assert_array_equal(p.A, np.zeros((3, 3)))
    np.testing.assert_array_equal(p.B, [-2 * sign] * 3)
    np.testing.assert_array_equal(p.F, sign * np.eye(3))
    CHECK.assertEqual(constraint.leq, leq)


@pytest.mark.parametrize("kind", ["variable", "expression", "theta"])
@pytest.mark.parametrize("reverse", [False, True])
def test_disequality_rejected(kind, reverse):
    """Disequality must never become a misleading Python boolean."""
    p = model()
    value = {"variable": p.x, "expression": 2 * p.x + 3, "theta": p.t}[kind]
    with pytest.raises(TypeError, match="Symbolic !="):
        operator.ne(2, value) if reverse else operator.ne(value, 2)
    CHECK.assertEqual(p.n_constraints, 0)


def test_foreign_nested_theta_rejection_is_atomic():
    """Ownership validation sees theta terms below sums and multiplications."""
    p, q = model(), model()
    with pytest.raises(ValueError, match="another program"):
        p.row = p.x <= 2 * (q.t + 3) - p.t
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertEqual(p.n_thetas, 3)
    CHECK.assertTrue(all(not v.cons_by for v in p.x))


@pytest.mark.parametrize("size", [2, 3, 5])
def test_whole_affine_sum(size):
    """
    Reduction retains unequal coefficients, repeated columns and constants.
    """
    p = model(size)
    coefficients = np.arange(1, size + 1)
    expression = p.x * coefficients.tolist() + p.x + 3
    reduced = sigma(expression)
    p.row = reduced <= ROW_BOUND
    p.o = inf(reduced)
    np.testing.assert_array_equal(p.A, [coefficients + 1])
    np.testing.assert_array_equal(p.B, [20 - 3 * size])
    np.testing.assert_array_equal(p.C, coefficients + 1)
    CHECK.assertEqual(p.o.constant, 3 * size)
    CHECK.assertIn("sigma", str(reduced))
    CHECK.assertIn(r"\sum", reduced.latex())
    for n, variable in enumerate(p.x):
        variable.X[0] = n + 2
    CHECK.assertEqual(
        reduced.solution()[0],
        sum((n + 2) * (n + 2) for n in range(size)) + 3 * size,
    )


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("reverse", [False, True])
def test_partial_expression_sum(axis, reverse):
    """
    Partial reduction keeps nonsummed coordinates and their requested order.
    """
    p = Prg()
    p.i, p.j = I(size=2), I(size=3)
    p.x = V(p.i, p.j)
    i = p.i[::-1] if reverse else p.i
    expression = 2 * p.x(i, p.j) + 3
    reduced = sigma(expression, (i, p.j)[axis], position=axis)
    p.row = reduced <= PARTIAL_BOUND
    expected = np.zeros((3 if axis == 0 else 2, 6))
    row_indices = [1, 0] if reverse else [0, 1]
    for a, original_i in enumerate(row_indices):
        for j in range(3):
            expected[j if axis == 0 else a, original_i * 3 + j] = 2
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(
        p.B,
        [30 - (6 if axis == 0 else 9)] * len(expected),
    )
    remaining = p.j if axis == 0 else i
    selected = reduced(remaining[::-1])
    p.selected = selected <= PARTIAL_BOUND
    row_count = len(expected)
    np.testing.assert_array_equal(p.A[row_count:], expected[::-1])
    p.o = inf(sigma(reduced, remaining))
    np.testing.assert_array_equal(p.C, [2] * 6)
    CHECK.assertEqual(p.o.constant, 18)


def test_theta_reduction_and_repeated_columns():
    """
    Reductions accumulate theta terms and preserve cancellation by column.
    """
    p = model()
    reduced = sigma(2 * p.x + 3 * (p.t + 0) + 4 - p.t)
    p.row = reduced <= ROW_BOUND
    np.testing.assert_array_equal(p.A, [[2, 2, 2]])
    np.testing.assert_array_equal(p.B, [8])
    np.testing.assert_array_equal(p.F, [[-2, -2, -2]])
    with pytest.raises(ValueError, match="Theta-dependent"):
        inf(reduced)


def test_expression_selection_preserves_theta_and_constants():
    """A selected F row set carries all compiled terms in selection order."""
    p = model()
    expression = 2 * p.x - 3 * (p.t + 0) + 4
    p.row = expression(p.i[::-2]) <= ROW_BOUND
    np.testing.assert_array_equal(p.A, 2 * np.eye(3)[[2, 0]])
    np.testing.assert_array_equal(p.B, [16, 16])
    np.testing.assert_array_equal(p.F, 3 * np.eye(3)[[2, 0]])


def _scalar_parameter_oracle(operation, reverse):
    """Evaluate numeric expectations independently of Gana dispatch."""
    return [
        operation(2, value) if reverse else operation(value, 2)
        for value in [1, 2, 3]
    ]


def _check_transformed_scalar(p, result):
    """Verify the new interval domain and separate matrix columns."""
    CHECK.assertIsInstance(result, T)
    CHECK.assertEqual(result._validated_bounds(), [(0, 10), (2, 12), (4, 14)])
    p.row = result <= ROW_BOUND
    np.testing.assert_array_equal(p.A, np.zeros((3, 3)))
    np.testing.assert_array_equal(p.B, [20] * 3)
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((3, 3)), -np.eye(3))),
    )


def _scalar_symbolic_oracle(kind, operation, reverse):
    """Derive affine coefficients and offsets from elementary arithmetic."""
    coefficient, constant = (2, 3) if kind == "expression" else (1, 0)
    if operation is operator.add:
        return coefficient, constant + 2
    if operation is operator.sub:
        return (
            -coefficient if reverse else coefficient,
            2 - constant if reverse else constant - 2,
        )
    return 2 * coefficient, 2 * constant


@pytest.mark.parametrize(
    "dtype",
    [np.int64, np.uint32, np.float32, np.float64],
)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "kind",
    ["variable", "expression", "theta", "parameter"],
)
@pytest.mark.parametrize(
    "operation",
    [operator.add, operator.sub, operator.mul],
)
def test_numpy_scalar_dispatch(dtype, reverse, kind, operation):
    """NumPy scalars use the same algebra and ownership as Python scalars."""
    p = model()
    value = {
        "variable": p.x,
        "expression": 2 * p.x + 3,
        "theta": p.t,
        "parameter": P(_=[1, 2, 3]),
    }[kind]
    result = (
        operation(dtype(2), value) if reverse else operation(value, dtype(2))
    )
    if kind == "parameter":
        expected = _scalar_parameter_oracle(operation, reverse)
        np.testing.assert_array_equal(result._, expected)
        return
    if kind == "theta" and operation is operator.mul:
        _check_transformed_scalar(p, result)
        return
    p.row = result <= ROW_BOUND
    coefficient, constant = _scalar_symbolic_oracle(kind, operation, reverse)
    expected_a = (
        np.zeros((3, 3)) if kind == "theta" else coefficient * np.eye(3)
    )
    expected_f = (
        -coefficient * np.eye(3) if kind == "theta" else np.zeros((3, 3))
    )
    np.testing.assert_array_equal(p.A, expected_a)
    np.testing.assert_array_equal(p.B, [20 - constant] * 3)
    np.testing.assert_array_equal(p.F, expected_f)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "operation",
    [operator.add, operator.sub, operator.mul],
)
def test_numpy_vector_dispatch(reverse, operation):
    """One-dimensional arrays align by row, including reflected operations."""
    p = model()
    values = np.array([2, 4, 8], dtype=np.float32)
    expression = 2 * p.x + 3
    result = (
        operation(values, expression)
        if reverse
        else operation(expression, values)
    )
    p.row = result <= ROW_BOUND
    coefficients = np.full(3, 2)
    constants = np.full(3, 3)
    if operation is operator.mul:
        coefficients, constants = coefficients * values, constants * values
    elif operation is operator.add:
        constants = constants + values
    else:
        coefficients = -coefficients if reverse else coefficients
        constants = values - constants if reverse else constants - values
    np.testing.assert_array_equal(p.A, np.diag(coefficients))
    np.testing.assert_array_equal(p.B, 20 - constants)


@pytest.mark.parametrize(
    "operation",
    [operator.floordiv, operator.mod, operator.pow, operator.truediv],
)
@pytest.mark.parametrize(
    "numerator",
    [2, np.int64(2), [2, 8, 16], np.array([2, 8, 16])],
)
def test_reflected_numeric_operations(operation, numerator):
    """
    Reflected division/remainder/power preserve operand order and coordinates.
    """
    p = model()
    p.data = P(p.i, _=[2, 4, 8])
    selected = p.data(p.i[::-1])
    result = operation(numerator, selected)
    values = [2] * 3 if np.ndim(numerator) == 0 else list(numerator)
    expected = [operation(int(a), b) for a, b in zip(values, [8, 4, 2])]
    np.testing.assert_array_equal(result._, expected)
    CHECK.assertEqual(tuple(result.map), tuple(selected.map))


@pytest.mark.parametrize(
    "kind",
    ["variable", "expression", "theta", "parameter"],
)
@pytest.mark.parametrize(
    "invalid",
    [[], [1, object()], object(), np.array([[1, 2]]), np.array([1j])],
)
def test_invalid_addends_fail_deliberately(kind, invalid):
    """Reject invalid operand domains before any model bookkeeping changes."""
    p = model()
    value = {
        "variable": p.x,
        "expression": 2 * p.x + 3,
        "theta": p.t,
        "parameter": P(_=2),
    }[kind]
    with pytest.raises((TypeError, ValueError)):
        value + invalid
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertEqual(p.n_thetas, 3)
