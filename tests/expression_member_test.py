"""Independent row, column and constant oracles for nested scalar operands."""

from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf, sigma

CHECK = TestCase()


def test_shifted_difference_keeps_source_member_coordinates():
    """
    Boundary rows reuse variables without inserting expression keys into
    owners.
    """
    p = Prg()
    p.i = I(size=3)
    p.x = V(p.i)
    members = list(p.x)
    keys = [tuple(member.map) for member in members]
    difference = p.x(p.i) - p.x(p.i - 1)
    p.balance = difference == 0
    np.testing.assert_array_equal(p.A, [[1, 0, 0], [-1, 1, 0], [0, -1, 1]])
    np.testing.assert_array_equal(p.B, [0, 0, 0])
    CHECK.assertEqual([tuple(member.map) for member in members], keys)
    CHECK.assertIs(difference[0].variables[0], members[0])


def model(size=3):
    """Register two independent vectors with stable, disjoint column IDs."""
    p = Prg()
    p.i = I(size=size)
    p.x, p.y = V(p.i), V(p.i)
    return p


@pytest.mark.parametrize("position", [0, 1, -1])
@pytest.mark.parametrize("lower", [False, True])
@pytest.mark.parametrize(
    "build, x_coefficient, y_coefficient, constant",
    [
        (lambda x, _y: 2 * x + 3, 2, 0, 3),
        (lambda x, _y: (2 * x + 3) + (x - 1), 3, 0, 2),
        (lambda x, y: (2 * x + 3) - (4 * y - 5), 2, -4, 8),
        (lambda x, _y: -(2 * x + 3), -2, 0, -3),
        (lambda x, y: ((2 * x + 3) / 2) + y, 1, 1, 1.5),
    ],
)
def test_nested_member_constraint(
    *,
    position,
    lower,
    build,
    x_coefficient,
    y_coefficient,
    constant,
):
    """Selected nested rows retain exact columns in both bound directions."""
    p = model()
    expression = build(p.x, p.y)[position]
    bound = 13
    p.row = bound <= expression if lower else expression <= bound
    sign = -1 if lower else 1
    expected = np.zeros((1, p.n_variables))
    column = position % len(p.i)
    expected[0, column] = sign * x_coefficient
    expected[0, len(p.i) + column] = sign * y_coefficient
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [sign * (bound - constant)])
    CHECK.assertEqual(p.n_constraints, 1)


@pytest.mark.parametrize("reverse", [False, True])
def test_distinct_members_on_both_sides(reverse):
    """Two scalar F operands preserve distinct positions and RHS offsets."""
    p = model()
    left, right = (2 * p.x + 3)[2], (4 * p.y - 5)[0]
    p.row = right <= left if reverse else left <= right
    sign = -1 if reverse else 1
    np.testing.assert_array_equal(p.A, [[0, 0, 2 * sign, -4 * sign, 0, 0]])
    np.testing.assert_array_equal(p.B, [-8 * sign])


@pytest.mark.parametrize("reverse", [False, True])
def test_nested_member_broadcast(reverse):
    """Broadcast one selected row without remapping its column per result."""
    p = model()
    selected = (2 * p.x + 3)[1]
    vector = 4 * p.y - 5
    p.row = vector <= selected if reverse else selected <= vector
    sign = -1 if reverse else 1
    expected = np.zeros((3, 6))
    expected[:, 1] = 2
    expected[:, 3:] = -4 * np.eye(3)
    np.testing.assert_array_equal(p.A, sign * expected)
    np.testing.assert_array_equal(p.B, [-8 * sign] * 3)


@pytest.mark.parametrize("position", [0, 1, 3, -1])
def test_multidimensional_nested_member(position):
    """A flat row selection over a Cartesian domain retains its one column."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=2)
    p.x = V(p.i, p.j)
    bound = 9
    p.row = (2 * p.x + 3)[position] == bound
    expected = np.zeros((1, 4))
    expected[0, position] = 2
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [6])


@pytest.mark.parametrize("lower", [False, True])
def test_theta_bound_on_nested_member(lower):
    """Align nested scalar coefficients and offsets with the selected theta."""
    p = model()
    p.t = T(p.i, _=[(0, 10)] * 3)
    member = (2 * p.x + 3)[1]
    p.row = member >= p.t[2] if lower else member <= p.t[2]
    sign = -1 if lower else 1
    np.testing.assert_array_equal(p.A, [[0, 2 * sign, 0, 0, 0, 0]])
    np.testing.assert_array_equal(p.B, [-3 * sign])
    np.testing.assert_array_equal(p.F, [[0, 0, sign]])


def test_member_reuse_preserves_snapshots_and_parent():
    """Retain the parent and numerical snapshot when reusing a child."""
    p = model()
    p.rate = P(p.i, _=[2, 4, 8], mutable=True)
    expression = p.rate * p.x + 3
    member = expression[1]
    keys = tuple(member.map)
    with pytest.warns(UserWarning, match="overwritten"):
        p.rate = P(p.i, _=[10, 20, 30])
    bound = 11
    p.one = member <= bound
    p.two = member + member <= bound
    np.testing.assert_array_equal(
        p.A,
        [[0, 4, 0, 0, 0, 0], [0, 8, 0, 0, 0, 0]],
    )
    np.testing.assert_array_equal(p.B, [8, 5])
    np.testing.assert_array_equal(expression.A, [[2], [4], [8]])
    CHECK.assertIs(member.parent, expression)
    CHECK.assertEqual(tuple(member.map), keys)


@pytest.mark.parametrize("field", ["X", "args", "Y", "Z"])
@pytest.mark.parametrize("consume", [False, True])
def test_scalar_metadata_is_independent_after_replay(field, consume):
    """Row edits preserve sibling state and escaped container identity."""
    p = model()
    expression = 2 * p.x + p.y
    dependent = expression + 1
    if consume:
        list(expression)
    first, second = expression[0], expression[1]
    held = getattr(first, field)
    expected = getattr(second, field).copy()
    if isinstance(held, dict):
        held[0] = 17
    else:
        held.append(17)
    CHECK.assertIs(getattr(first, field), held)
    CHECK.assertIs(expression[0], first)
    CHECK.assertEqual(getattr(second, field), expected)
    CHECK.assertEqual(getattr(expression[2], field), expected)
    CHECK.assertEqual(dependent[0].A, [2, 1])
    CHECK.assertEqual(dependent[0].B, -1)


@pytest.mark.parametrize("wrapped", [False, True])
def test_variable_valued_axis_selection_preserves_rows(wrapped):
    """Variable axes match singleton wrappers without symbolic comparisons."""
    p = Prg()
    p.axis = V()
    p.i = I(size=3)
    p.x = V(p.axis, p.i)
    axis = [p.axis] if wrapped else p.axis
    CHECK.assertIs(p.x(axis, p.i), p.x)
    bound = 9
    p.c = 2 * p.x(axis, p.i) + 3 <= bound
    expected = np.zeros((3, 4))
    expected[:, 1:] = 2 * np.eye(3)
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [6, 6, 6])
    CHECK.assertIs(p.c[1].variables[0], p.x[1])


def test_union_domain_exact_selection_retains_owner():
    """Set-backed union domains retain exact-selection identity and order."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=2)
    p.x = V((p.i, p.j))
    keys = tuple(p.x.map)
    CHECK.assertIs(p.x(*p.x.index), p.x)
    CHECK.assertEqual(tuple(p.x.map), keys)


def test_nested_member_solver(tmp_path, monkeypatch):
    """The exported model reaches x[1]=4 and objective 2*x[1]+3=11."""
    pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = model()
    member = (2 * p.x + 3)[1]
    lower, upper = 4, 15
    p.lower = p.x[1] >= lower
    p.upper = member <= upper
    p.o = inf(sigma(member))
    p.opt()
    np.testing.assert_allclose(p.o.X, 11, rtol=0, atol=1e-9)
