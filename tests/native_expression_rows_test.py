"""
Read-only row projection, shared identity, and promotion on mutable edits.
"""

import pickle
from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V, sigma
from gana.backends.native.algebra import _LEGACY

CHECK = TestCase()


def model(size=12):
    """Use disjoint symbol columns and coordinate-dependent coefficients."""
    p = Prg()
    p.i = I(size=size)
    p.x, p.y = V(p.i), V(p.i)
    p.k = P(p.i, _=list(range(1, size + 1)))
    p.t = T(p.i, _=(-2, 3))
    return p


def build(p, kind):
    """Exercise normalization, theta terms, and compact reduction formats."""
    expressions = {
        "binary": lambda: p.k * p.x + 3,
        "nested": lambda: (p.k * p.x - 4 * p.y) + 3,
        "negate": lambda: -(p.k * p.x + 3),
        "scale": lambda: 2 * (p.k * p.x + 3),
        "theta": lambda: p.k * p.x - p.t,
        "anonymous": lambda: p.k * p.x + T(p.i, _=(-2, 3)),
        "sum": lambda: sigma(p.k * p.x + 3),
        "vsum": lambda: sigma(p.x),
    }
    return expressions[kind]()


def signature(row):
    """
    Compare public scalar metadata independently of implementation classes.
    """
    return (
        row.A,
        row.B,
        row.P,
        str(row),
        row.latex(),
        row.pos,
        row.n,
        row.case,
        row.struct,
    )


@pytest.mark.parametrize(
    "kind",
    [
        "binary",
        "nested",
        "negate",
        "scale",
        "theta",
        "anonymous",
        "sum",
        "vsum",
    ],
)
@pytest.mark.parametrize("position", [0, -1])
def test_row_projection_matches_legacy_without_siblings(kind, position):
    """A first read must match the existing frontend without full replay."""
    actual = build(model(), kind)
    token = _LEGACY.set(True)
    try:
        expected = build(model(), kind)
    finally:
        _LEGACY.reset(token)
    row = actual[position]
    CHECK.assertEqual(signature(row), signature(expected[position]))
    CHECK.assertNotIn("_legacy_cache", actual.__dict__)
    CHECK.assertIs(row, actual[position])
    CHECK.assertIs(row.parent, actual)
    CHECK.assertEqual(len(actual._native_rows), 1)


def test_selection_read_retains_only_requested_rows():
    """
    Reverse/nested views and list slices share exactly their requested rows.
    """
    p = model(1000)
    expression = p.k * p.x + 3
    reverse = expression(p.i[::-1])
    selected = reverse(p.i[::2])
    row = selected[-1]
    CHECK.assertIs(row, expression[998])
    CHECK.assertIs(row, reverse[1])
    CHECK.assertEqual(row.A, [999])
    CHECK.assertEqual(len(expression._native_rows), 1)
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)
    CHECK.assertEqual([r.P for r in selected[:2]], [[0], [2]])
    CHECK.assertEqual(len(expression._native_rows), 3)


@pytest.mark.parametrize(
    "edit",
    ["item", "slice", "append", "replace", "mapping"],
)
def test_edits_promote_before_mutation_and_preserve_snapshots(edit):
    """
    Escaped rows and lists survive promotion; existing arithmetic is frozen.
    """
    p = model()
    source = p.k * p.x
    selected = source(p.i[:2])
    derived = 3 * selected + 5
    row = source[0]
    coefficients = row.A
    CHECK.assertNotIn("_legacy_cache", source.__dict__)
    if edit == "item":
        coefficients[0] = 19
    elif edit == "slice":
        coefficients[:] = [19]
    elif edit == "append":
        row.Y.append(19)
    elif edit == "replace":
        row.B = 19
    else:
        row.X[2] = 19
    CHECK.assertIs(source[0], row)
    CHECK.assertIs(selected[0], row)
    CHECK.assertIs(row.A, coefficients)
    CHECK.assertEqual([r.A for r in derived], [[3], [6]])
    CHECK.assertEqual([r.B for r in derived], [-5, -5])
    CHECK.assertIn("_legacy_cache", source.__dict__)


# The pickle branch reads only bytes generated from this test's own fixture.
@pytest.mark.parametrize(
    "clone",
    [deepcopy, lambda value: pickle.loads(pickle.dumps(value))],
)
def test_copy_after_row_read_preserves_graph_aliases(clone):
    """
    Explicit serialization may replay but must preserve escaped identities.
    """
    p = model()
    source = p.k * p.x + 3
    row = source[2]
    copied_source, copied_row, copied_list = clone((source, row, row.A))
    CHECK.assertIs(copied_source[2], copied_row)
    CHECK.assertIs(copied_row.A, copied_list)
    copied_list[0] = 27
    CHECK.assertEqual(source[2].A, [3])
    CHECK.assertEqual(copied_source[2].A, [27])


def test_compact_selector_single_positions_and_last_duplicates():
    """
    Native selector access validates bounds and preserves duplicate order.
    """
    p = model(4)
    repeated = p.i[:]
    repeated._ = [p.i[3], p.i[1], p.i[3]]
    source = 2 * p.x
    selected = source(repeated)
    selector = selected._native_row_selector
    CHECK.assertEqual([selector.at(n) for n in range(3)], [3, 1, 3])
    CHECK.assertEqual(selector.last(3), 2)
    CHECK.assertIsNone(selector.last(0))
    with pytest.raises(IndexError):
        selector.at(3)
    with pytest.raises(OverflowError):
        selector.at(-1)


def test_partial_iteration_and_matrix_read_remain_lazy():
    """An abandoned iterator and a single column aggregation create one row."""
    p = model(1000)
    source = p.k * p.x + p.y + p.x
    row = next(iter(source))
    CHECK.assertEqual(row.matrix, {0: 2, 1000: 1})
    CHECK.assertNotIn("_legacy_cache", source.__dict__)
    CHECK.assertEqual(len(source._native_rows), 1)
    columns = row.matrix
    columns[0] = 19
    CHECK.assertEqual(columns, {0: 19, 1000: 1})
    CHECK.assertIs(source[0].matrix, columns)


def test_shared_theta_metadata_survives_promotion():
    """Sibling theta-owner metadata stays a single shared mutable list."""
    p = model()
    source = p.k * p.x - p.t
    left, right = source[0], source[1]
    CHECK.assertIs(left.rhs_thetas, right.rhs_thetas)
    shared = left.rhs_thetas
    shared.append("marker")
    CHECK.assertIs(source.rhs_thetas, shared)
    CHECK.assertIs(source[2].rhs_thetas, shared)
    CHECK.assertIs(right.rhs_thetas, shared)


@pytest.mark.parametrize("variable", [False, True])
@pytest.mark.parametrize("width", [2, 3, 5])
@pytest.mark.parametrize("position", [None, 1])
def test_partial_reduction_projects_only_one_output_group(
    variable,
    width,
    position,
):
    """A grouped reduction builds the requested terms without other outputs."""
    p = Prg()
    p.i, p.j = I(size=100), I(size=width)
    p.x = V(p.i, p.j)
    source = p.x if variable else 2 * p.x + 3
    reduced = sigma(source, p.j, position=position)
    row = reduced[7]
    CHECK.assertEqual(row.P, list(range(7 * width, 8 * width)))
    CHECK.assertEqual(row.A, [1 if variable else 2] * width)
    CHECK.assertNotIn("_legacy_cache", reduced.__dict__)
    CHECK.assertEqual(len(reduced._native_rows), 1)


def test_register_after_first_read_updates_shared_number():
    """
    A retained scalar sees later view registration without sibling creation.
    """
    p = model()
    source = p.k * p.x
    row = source[3]
    p.expression = source
    p.selected = source(p.i[3:5])
    CHECK.assertEqual(row.n, 12)
    CHECK.assertIs(p.selected[0], row)
    CHECK.assertNotIn("_legacy_cache", source.__dict__)


def test_saved_solution_read_stays_lazy_after_variable_history_edit():
    """Use captured solve values without overwriting later public V edits."""
    p = Prg()
    p.i = I(size=100)
    p.x = V(p.i)
    bound = 9
    p.c = 2 * p.x + 3 <= bound
    p._load_values(([2.0] * 100, 0))
    p.x[7].X[0] = 99
    expression = p.c.function
    CHECK.assertEqual(expression[7].X[0], -2)
    CHECK.assertEqual(p.x[7].X[0], 99)
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)
    CHECK.assertEqual(len(expression._native_rows), 1)


def test_iterator_observes_public_list_growth_after_promotion():
    """
    A paused iterator retains ordinary list behavior when its owner grows.
    """
    p = model(4)
    source = 2 * p.x
    iterator = iter(source)
    first = next(iterator)
    source._.append(first)
    CHECK.assertEqual([row.P for row in iterator], [[1], [2], [3], [0]])


@pytest.mark.parametrize("variable", [False, True])
def test_reduction_rows_keep_independent_theta_metadata(variable):
    """Reduction rows own their theta lists even when those lists are empty."""
    p = Prg()
    p.i, p.j = I(size=3), I(size=3)
    p.x = V(p.i, p.j)
    reduced = sigma(p.x if variable else 2 * p.x, p.j)
    left, right = reduced[0], reduced[1]
    CHECK.assertIsNot(left.rhs_thetas, right.rhs_thetas)
    left.rhs_thetas.append("marker")
    CHECK.assertEqual(right.rhs_thetas, [])
    CHECK.assertEqual(reduced.rhs_thetas, [])
