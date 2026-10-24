"""
Public indexing oracles shared by Python and native coordinate selections.
"""

import copy
import gc
import pickle
import weakref
from itertools import product
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V, inf, sigma
from gana.storage.parameters import NATIVE

CHECK = TestCase()


def model(kind, size=4):
    """
    Build a rectangular owner with independently predictable numeric
    values.
    """
    p = Prg()
    p.i, p.j = I(size=size), I(size=3)
    args = {P: {"_": list(range(size * 3))}, V: {}, T: {"_": (-2, 7)}}[kind]
    p.e = kind(p.i, p.j, mutable=True, **args)
    return p


def value(member, kind):
    """Compare values or stable column IDs rather than symbolic equality."""
    if member is None or kind is P:
        return member
    return member.n


def requested_axes(p, rows, columns):
    """Translate the integer oracle's coordinates into public index members."""
    return tuple(
        tuple(None if n is None else axis[n] for n in ids)
        for axis, ids in zip((p.i, p.j), (rows, columns))
    )


def expected_mapping(kind, axes, values):
    """
    Apply each documented skip policy to an ordinary insertion-ordered
    dict.
    """
    result = {}
    for key, item in zip(product(*axes), values):
        skipped = any(atom is None for atom in key)
        if kind is T and skipped:
            continue
        result[None if kind is P and skipped else key] = item
    return result


def expected_values(rows, columns):
    """
    Compute row-major values independently of native coordinate machinery.
    """
    return [
        None if i is None or j is None else i * 3 + j
        for i, j in product(rows, columns)
    ]


@pytest.mark.parametrize("kind", [P, V, T])
@pytest.mark.parametrize(
    "rows,columns",
    [
        ([3, 1], [2, 0]),
        ([0, 2, 3], [1]),
        ([], [0, 1]),
        ([1, 1, 0], [2, 2, 1]),
        ([None, 0, 2], [1, None, 2]),
    ],
)
def test_product_order_maps_and_gaps(kind, rows, columns):
    """
    Ordering, duplicates and skipped keys match the independent Python
    oracle.
    """
    p = model(kind)
    axes = requested_axes(p, rows, columns)
    selected = p.e(*axes)
    expected = expected_values(rows, columns)
    expected_map = expected_mapping(kind, axes, expected)
    CHECK.assertEqual([value(item, kind) for item in selected._], expected)
    CHECK.assertEqual(list(selected.map), list(expected_map))
    CHECK.assertEqual(
        [value(item, kind) for item in selected.map.values()],
        list(expected_map.values()),
    )
    CHECK.assertEqual(len(selected.map), len(expected_map))
    CHECK.assertEqual(
        len(selected),
        len(expected) if kind is V else len(expected_map),
    )


@pytest.mark.parametrize("kind", [P, V, T])
def test_nested_selection_and_missing_membership(kind):
    """
    Nested reversed views keep source membership rather than querying the
    root.
    """
    p = model(kind)
    selected = p.e(p.i[::-1], p.j[::2])
    nested = selected(p.i[1:3], p.j[2])
    CHECK.assertEqual([value(item, kind) for item in nested._], [5, 8])
    if kind is V:
        CHECK.assertEqual(list(selected(p.i[0], p.j[1])._), [None])
    else:
        with pytest.raises(KeyError) as error:
            selected(p.i[0], p.j[1])
        CHECK.assertEqual(error.value.args[0], (p.i[0], p.j[1]))


@pytest.mark.parametrize("kind", [P, V, T])
def test_nested_gaps_and_independent_local_edits(kind):
    """Exceptional containers retain legacy independent map/list mutation."""
    p = model(kind)
    selected = p.e([None, p.i[1]], p.j)
    nested = selected(p.i[1], p.j[1:])
    CHECK.assertEqual([value(item, kind) for item in nested._], [4, 5])
    key = (p.i[1], p.j[1])
    selected._[4] = None
    CHECK.assertEqual(value(selected.map[key], kind), 4)
    selected.map[key] = None
    CHECK.assertEqual([value(item, kind) for item in nested._], [4, 5])
    CHECK.assertEqual(list(selected(p.i[1], p.j[1])._), [None])


@pytest.mark.parametrize("kind", [P, V, T])
def test_empty_product_ignores_other_missing_axes(kind):
    """An empty product does not look up another axis's absent coordinates."""
    p = model(kind)
    selected = p.e(p.i[:0], [object()])
    CHECK.assertEqual(list(selected._), [])
    CHECK.assertEqual(dict(selected.map), {})


@pytest.mark.parametrize("kind", [P, V, T])
def test_irregular_domain_and_retained_growth(kind):
    """
    Unions and post-growth owners preserve registration order and old
    views.
    """
    p = Prg()
    p.i, p.j = I(size=3), I(size=2)
    args = {P: {"_": [10, 11, 12, 13]}, V: {}, T: {"_": (0, 2)}}[kind]
    p.e = kind((p.i[:2], p.j[:1]), (p.i[1:], p.j[1:]), mutable=True, **args)
    selected = p.e(p.i[1], p.j[::-1])
    CHECK.assertEqual(
        [value(item, kind) for item in selected._],
        [12, 11] if kind is P else [2, 1],
    )
    args = {P: {"_": [20]}, V: {}, T: {"_": (0, 2)}}[kind]
    p.e = kind(p.i[0], p.j[1], **args)
    CHECK.assertEqual(
        [value(item, kind) for item in selected._],
        [12, 11] if kind is P else [2, 1],
    )
    grown = p.e(p.i[:2], p.j[1])
    CHECK.assertEqual(
        [value(item, kind) for item in grown._],
        [20, 12] if kind is P else [4, 2],
    )


@pytest.mark.parametrize("kind", [P, V, T])
@pytest.mark.parametrize("gaps", [False, True])
def test_selection_serialization_and_lifetime(kind, gaps):
    """
    Views outlive programs and serialize with consistent coordinates and
    data.
    """
    p = model(kind)
    rows = [None, p.i[1]] if gaps else p.i[::2]
    selected = p.e(rows, p.j[::-1])
    expected = [value(item, kind) for item in selected._]
    for restored in (
        copy.deepcopy(selected),
        pickle.loads(pickle.dumps(selected)),
    ):
        CHECK.assertEqual([value(item, kind) for item in restored._], expected)
    reference = weakref.ref(p)
    del p
    gc.collect()
    CHECK.assertIsNone(reference())
    CHECK.assertEqual([value(item, kind) for item in selected._], expected)


@pytest.mark.skipif(not NATIVE, reason="native storage ownership contract")
def test_cartesian_parameter_snapshots_detach_after_nested_selection():
    """
    Nested products retain old values even after root and selection writes.
    """
    p = model(P)
    selected = p.e(p.i[::-1], p.j[::2])
    nested = selected(p.i[1:3], p.j[2])
    p.e._[:] = [99] * 12
    selected._[1] = 55
    CHECK.assertEqual(list(nested._), [5, 8])
    CHECK.assertEqual(list(selected._), [9, 55, 6, 8, 3, 5, 0, 2])
    CHECK.assertEqual(list(p.e._), [99] * 12)


@pytest.mark.skipif(not NATIVE, reason="native lazy member contract")
@pytest.mark.parametrize("kind", [V, T])
@pytest.mark.parametrize("gaps", [False, True])
def test_selection_does_not_materialize_scalar_members(kind, gaps):
    """Large selections and membership checks must leave scalar state empty."""
    p = model(kind, size=1000)
    rows = [None, *p.i[::2]] if gaps else p.i[::2]
    selected = p.e(rows, p.j[::-1])
    _ = len(selected), len(selected.map), (p.i[0], p.j[0]) in selected.map
    CHECK.assertEqual(p.e._symbol_storage.states, {})
    nested = selected(p.i[0], p.j[0])
    CHECK.assertEqual(p.e._symbol_storage.states, {})
    CHECK.assertIs(nested[0], p.e[0])


def test_selected_native_algebra_has_correct_global_columns():
    """
    Cartesian selection and reduction compile coefficients in global order.
    """
    p = model(V)
    p.k = P(p.i, p.j, _=list(range(1, 13)))
    p.o = inf(sigma(p.k(p.i[::-2], p.j[::2]) * p.e(p.i[::-2], p.j[::2])))
    CHECK.assertEqual(list(p.C), [0, 0, 0, 4, 0, 6, 0, 0, 0, 10, 0, 12])


def test_skipped_parameter_values_are_captured_before_root_writes():
    """
    Skipped views hold numerical snapshots even when their values are
    unread.
    """
    p = model(P)
    selected = p.e([None, p.i[1]], p.j[:1])
    p.e._[3] = 99
    CHECK.assertEqual(list(selected._), [None, 3])


def test_missing_variable_does_not_appear_after_owner_growth():
    """
    A gap is fixed membership even if the mutable root later gains its key.
    """
    p = model(V)
    p.extra = I("extra")
    selected = p.e(p.extra, p.j)
    p.e = V(p.extra, p.j)
    CHECK.assertEqual(list(selected._), [None, None, None])


@pytest.mark.parametrize("kind", [P, T])
def test_skips_do_not_hide_non_skipped_missing_coordinates(kind):
    """
    Skipping one row must not suppress the first real missing-coordinate
    error.
    """
    p = model(kind)
    p.extra = I("extra")
    with pytest.raises(KeyError) as error:
        p.e([None, p.extra[0]], p.j[:1])
    CHECK.assertEqual(error.value.args[0], (p.extra[0], p.j[0]))


@pytest.mark.skipif(
    not NATIVE,
    reason="native missing-coordinate construction",
)
def test_missing_variables_do_not_replay_python_coordinate_lookups(
    monkeypatch,
):
    """V gaps must not walk the product just to build a suppressed KeyError."""
    p = model(V, size=100)
    p.extra = I("extra")

    def reject_lookup(_positions, _key):
        """Fail if construction crosses the scalar lookup boundary."""
        message = "selection expanded Python coordinates"
        raise AssertionError(message)

    monkeypatch.setattr(
        type(p.e._symbol_storage.positions),
        "__getitem__",
        reject_lookup,
    )
    selected = p.e([*p.i, p.extra[0]], p.j)
    CHECK.assertEqual(len(selected), 303)
    CHECK.assertEqual(p.e._symbol_storage.states, {})
