"""Selective bookkeeping must retain legacy ordering, aliases and edits."""

import pickle
from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, P, Prg, V, sigma
from gana.backends.native import constraint_rows as native_constraint_rows
from gana.backends.native.constraints import compile_program
from gana.storage.parameters import NATIVE

CHECK = TestCase()
pytestmark = pytest.mark.skipif(
    not NATIVE,
    reason="requires native membership",
)


def model(size=8):
    """
    Use two owners whose constraints overlap in different registration
    orders.
    """
    p = Prg()
    p.i = I(size=size)
    p.x, p.y = V(p.i), V(p.i)
    first_bound, middle_bound, last_bound = 8, 9, 10
    p.first = 2 * p.y <= first_bound
    p.middle = p.x + p.y <= middle_bound
    p.last = 3 * p.x <= last_bound
    return p


def identities(rows):
    """Compare object identities without invoking symbolic equality."""
    return list(map(id, rows))


def clone_fixture(value, method):
    """Clone only trusted fixtures generated within these regression tests."""
    return (
        deepcopy(value)
        if method is deepcopy
        else pickle.loads(pickle.dumps(value))
    )


def test_selective_links_and_positions_keep_native_compilation():
    """An overlapping row fills only the matching members of each batch."""
    p = model()
    x, y = p.x[3], p.y[3]
    links = x.cons_by
    CHECK.assertEqual(identities(links), identities([p.middle[3], p.last[3]]))
    CHECK.assertEqual(p.middle[3].cons_by_pos, {x: 0, y: 1})
    CHECK.assertEqual(
        identities(y.cons_by),
        identities([p.first[3], p.middle[3]]),
    )
    for source in p.constraint_sets:
        CHECK.assertEqual(set(source._native_rows), {3})
        CHECK.assertNotIn("_legacy_cache", source.__dict__)
        CHECK.assertNotIn("_legacy_cache", source.function.__dict__)
    CHECK.assertIs(x.cons_by, links)
    CHECK.assertIsNotNone(compile_program(p))


@pytest.mark.parametrize("kind", ["repeat", "cancel", "zero", "reduce"])
def test_repeated_and_zero_terms_preserve_membership(kind):
    """
    Stored occurrences register once per row, even when coefficients
    cancel.
    """
    p = model()
    p.zeros = P(p.i, _=[0] * len(p.i))
    expressions = {
        "repeat": lambda: p.x + p.x,
        "cancel": lambda: p.x - p.x,
        "zero": lambda: p.zeros * p.x,
        "reduce": lambda: sigma(p.x + p.x),
    }
    bound = 20
    p.extra = expressions[kind]() <= bound
    position = 0 if kind == "reduce" else 3
    links = p.x[3].cons_by
    CHECK.assertEqual(
        identities(links),
        identities(
            [
                p.middle[3],
                p.last[3],
                p.extra[position],
            ],
        ),
    )
    CHECK.assertEqual(len(p.extra._native_rows), 1)
    CHECK.assertIsNotNone(compile_program(p))


def test_missing_member_and_disjoint_selection_create_no_unrelated_rows():
    """
    A query outside a selected subdomain does not project that
    constraint.
    """
    p = model()
    bound = 7
    p.selected = 4 * p.x(p.i[::2]) <= bound
    CHECK.assertEqual(len(p.x[3].cons_by), 2)
    CHECK.assertNotIn("_native_rows", p.selected.__dict__)
    CHECK.assertIs(p.x[4].cons_by[-1], p.selected[2])
    CHECK.assertEqual(set(p.selected._native_rows), {2})


def test_existing_wrapper_does_not_force_registration_replay():
    """A scalar handle alone does not request its constraint membership."""
    p = model()
    held = p.x[3]
    bound = 7
    p.extra = 4 * p.x <= bound
    CHECK.assertIs(held, p.x[3])
    CHECK.assertNotIn("_native_rows", p.extra.__dict__)
    CHECK.assertNotIn("_legacy_cache", p.extra.__dict__)


@pytest.mark.parametrize("empty", [False, True])
def test_escaped_list_observes_later_registration(empty):
    """Already exposed membership lists update without expanding other rows."""
    p = model()
    p.z = V(p.i)
    variable = p.z[3] if empty else p.x[3]
    values = variable.cons_by
    before = identities(values)
    root = p.z if empty else p.x
    bound = 7
    p.extra = 4 * root <= bound
    CHECK.assertIs(variable.cons_by, values)
    CHECK.assertEqual(identities(values), [*before, id(p.extra[3])])
    CHECK.assertEqual(set(p.extra._native_rows), {3})
    CHECK.assertNotIn("_legacy_cache", p.extra.__dict__)


def test_partial_then_full_replay_preserves_aliases_and_order():
    """
    Promoting an earlier batch does not duplicate selectively
    registered rows.
    """
    p = model()
    x = p.x[3]
    values = x.cons_by
    middle, last = values
    positions = middle.cons_by_pos
    p.last._materialize()
    CHECK.assertIs(x.cons_by, values)
    CHECK.assertEqual(identities(values), [id(middle), id(last)])
    CHECK.assertIs(middle.cons_by_pos, positions)
    for variable in (p.x[3], p.y[3], p.x[5], p.y[5]):
        for position, row in enumerate(variable.cons_by):
            CHECK.assertEqual(row.cons_by_pos[variable], position)


@pytest.mark.parametrize("mutation", ["reverse", "clear", "pop"])
def test_first_list_edit_matches_materialized_reference(mutation):
    """Resolved list edits match ordinary rows without expanding siblings."""
    p, reference = model(), model()
    for source in reference.constraint_sets:
        source._materialize()
    values = p.x[3].cons_by
    getattr(values, mutation)()
    getattr(reference.x[3].cons_by, mutation)()
    CHECK.assertIs(p.x[3].cons_by, values)
    CHECK.assertEqual(
        [row.parent.pname for row in values],
        [row.parent.pname for row in reference.x[3].cons_by],
    )
    CHECK.assertIsNotNone(compile_program(p))
    for source in (p.middle, p.last):
        CHECK.assertEqual(set(source._native_rows), {3})
        CHECK.assertNotIn("_legacy_cache", source.__dict__)


def test_explicit_list_replacement_keeps_callers_object():
    """
    Explicit assignment preserves the exact public list, including
    updates.
    """
    p = model()
    replacement = []
    p.x[3].cons_by = replacement
    CHECK.assertIs(p.x[3].cons_by, replacement)
    bound = 7
    p.extra = 4 * p.x <= bound
    CHECK.assertIs(p.x[3].cons_by, replacement)
    CHECK.assertEqual(identities(replacement), [id(p.extra[3])])


def test_unregister_repairs_positions_without_expanding_siblings():
    """Detaching one partially observed set preserves all other live links."""
    p = model()
    values = p.x[3].cons_by
    middle, last = values
    positions = middle.cons_by_pos
    p.middle.unregister_variables()
    CHECK.assertEqual(identities(values), [id(last)])
    CHECK.assertEqual(last.cons_by_pos[p.x[3]], 0)
    CHECK.assertEqual(positions, {})
    CHECK.assertEqual(set(p.middle._native_rows), {3})
    CHECK.assertNotIn("_legacy_cache", p.middle.__dict__)
    p.middle.update_variables()
    CHECK.assertEqual(identities(values), [id(last), id(middle)])


def test_constraint_replacement_updates_escaped_membership():
    """
    Program reassignment removes the old occurrence and registers the
    new.
    """
    p = model()
    values = p.x[3].cons_by
    old = p.middle[3]
    bound = 21
    p.middle = 5 * p.x <= bound
    CHECK.assertIs(p.x[3].cons_by, values)
    CHECK.assertNotIn(id(old), identities(values))
    CHECK.assertEqual(identities(values), identities([p.last[3], p.middle[3]]))
    for position, row in enumerate(values):
        CHECK.assertEqual(row.cons_by_pos[p.x[3]], position)


def test_function_edit_before_membership_uses_compatibility_rows():
    """A changed coefficient cannot leave a stale native membership source."""
    p = model()
    p.middle.function[3].A[0] = 5
    values = p.x[3].cons_by
    CHECK.assertEqual(identities(values), identities([p.middle[3], p.last[3]]))
    CHECK.assertEqual(p.middle[3].A[0], 5)


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("clone", [deepcopy, pickle])
@pytest.mark.parametrize("warm", [False, True])
def test_copy_after_membership_read_keeps_one_graph(empty, clone, warm):
    """
    Derived indexes never leak into serialization or split copied
    aliases.
    """
    p = model()
    bound = 7
    p.selected = 4 * p.x(p.i[::2]) <= bound
    values = p.x[3 if empty else 4].cons_by
    if warm:
        _ = p.x[0].cons_by
        _ = p.x[1].cons_by
    # This roundtrip consumes only bytes created from the local fixture.
    copied = clone_fixture(p, clone)
    position = 3 if empty else 4
    CHECK.assertIs(p.x[position].cons_by, values)
    CHECK.assertIsNot(copied.x[position].cons_by, values)
    CHECK.assertIs(copied.x[position].cons_by[0], copied.middle[position])
    CHECK.assertEqual(copied.A, p.A)


def test_variable_defaults_do_not_share_mutable_scalar_state():
    """
    The cached constructor template preserves independent member
    metadata.
    """
    p = model()
    first, second = p.x[0], p.x[1]
    first.P[0] = 9
    first.eval_funcs["custom"] = "marker"
    first.evaluation["custom"] = 11
    first.X[2] = 4
    CHECK.assertEqual(second.P, [None])
    CHECK.assertEqual(second.eval_funcs, {})
    CHECK.assertEqual(second.evaluation, {})
    CHECK.assertEqual(second.X, {})


def test_growth_uses_captured_constructor_metadata_for_each_generation():
    """
    A shared default template retains registration metadata across
    growth.
    """
    p = Prg()
    p.i, p.j = I("a", "b"), I("c", "d")
    p.x = V(p.i, mutable=True, tag="initial", itg=True)
    first = p.x[0]
    p.x.tag = "changed root"
    p.x = V(p.j, tag="growth", itg=True)
    CHECK.assertEqual((first.tag, p.x[1].tag), ("initial", "initial"))
    CHECK.assertEqual(
        (p.x[2].tag, p.x[3].tag),
        ("changed root", "changed root"),
    )
    CHECK.assertEqual([value.itg for value in p.x], [True, True, True, True])
    CHECK.assertEqual([value.nn for value in p.x], [True, True, True, True])


def test_membership_dictionary_edit_preserves_escaped_mapping():
    """A resolved position-map edit stays local and survives later replay."""
    p = model()
    row = p.middle[3]
    positions = row.cons_by_pos
    positions[p.x[3]] = 42
    CHECK.assertIs(row.cons_by_pos, positions)
    CHECK.assertEqual(positions[p.x[3]], 42)
    CHECK.assertIs(p.middle[3], row)
    CHECK.assertIsNotNone(compile_program(p))
    CHECK.assertNotIn("_legacy_cache", p.middle.__dict__)
    p.middle._materialize()
    CHECK.assertIs(row.cons_by_pos, positions)
    CHECK.assertEqual(positions[p.x[3]], 42)
    CHECK.assertIsNone(compile_program(p))


@pytest.mark.parametrize("axis_size", [2, 3, 4])
def test_nested_variable_sum_coordinates_survive_replacement(
    axis_size,
):
    """
    Energy balance reductions remain lazy until row or replacement
    access.
    """
    p = Prg()
    p.i, p.j = I(size=3), I(size=axis_size)
    p.x, p.total = V(p.i, p.j), V(p.i)
    held = p.x[0]
    p.balance = p.total - sigma(p.x, p.j) == 0
    row = p.balance[1]
    CHECK.assertEqual(row.A, [1, *([-1] * axis_size)])
    CHECK.assertEqual(
        row.P,
        [3 * axis_size + 1, *range(axis_size, 2 * axis_size)],
    )
    CHECK.assertIs(held.cons_by[0], p.balance[0])
    p.balance = 2 * p.total - sigma(p.x, p.j) == 0
    CHECK.assertEqual(p.balance[1].A, [2, *([-1] * axis_size)])
    CHECK.assertIs(held.cons_by[0], p.balance[0])


def observe_projection(monkeypatch, source, stage):
    """Replay once during projection without replacing the constraint class."""
    target = (
        native_constraint_rows
        if stage == "operand"
        else native_constraint_rows.C
    )
    name = "_function" if stage == "operand" else "__init__"
    original = getattr(target, name)
    armed = True

    def promote(*args, **kwargs):
        """Permit nested replay constructors after the first observer fires."""
        nonlocal armed
        result = original(*args, **kwargs)
        if armed:
            armed = False
            source._materialize()
        return result

    monkeypatch.setattr(target, name, promote)


@pytest.mark.parametrize("stage", ["operand", "constraint"])
@pytest.mark.parametrize("access", ["row", "membership"])
@pytest.mark.parametrize("warm", [False, True])
def test_projection_reuses_rows_after_observer_promotion(
    monkeypatch,
    stage,
    access,
    warm,
):
    """Observer replay preserves row identity and export numbers."""
    p = model()
    if warm:
        _ = p.middle[0]
        _ = p.middle[1]
    observe_projection(monkeypatch, p.middle, stage)
    if access == "membership":
        CHECK.assertEqual(len(p.x[3].cons_by), 2)
    row = p.middle[3]
    CHECK.assertIs(row, p.middle[3])
    CHECK.assertIs(row, p.middle._[3])
    row.n = 42
    CHECK.assertEqual(row.n, 42)
    CHECK.assertIs(p.x[3].cons_by[0], row)
    CHECK.assertEqual(len(p.x[3].cons_by), 2)


@pytest.mark.parametrize("clone", [deepcopy, pickle])
def test_direct_constraint_copy_after_empty_membership_query(clone):
    """Direct constraint copies retain one graph after a missing match."""
    p = Prg()
    p.i = I(size=4)
    p.x = V(p.i)
    bound = 9
    p.c = 2 * p.x(p.i[::2]) <= bound
    CHECK.assertEqual(p.x[1].cons_by, [])
    # Only trusted bytes created from this fixture are deserialized here.
    copied = clone_fixture(p.c, clone)
    row = copied[0]
    values = row.variables[0].cons_by
    CHECK.assertEqual(len(values), 1)
    CHECK.assertIs(values[0], row)
    CHECK.assertIsNot(row, p.c[0])
    CHECK.assertEqual(row.A, [2])
