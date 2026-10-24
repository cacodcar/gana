"""Lazy constraint coefficients, identities and bookkeeping regressions."""

import pickle
from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V, sigma
from gana.backends.native.constraints import compile_program
from gana.backends.native.export import renumber
from gana.sets.constraint import C
from gana.storage.parameters import NATIVE

pytestmark = pytest.mark.skipif(
    not NATIVE,
    reason="requires native constraint projection",
)
CHECK = TestCase()


def model(size=12):
    """Use coordinate-dependent coefficients and separate variable owners."""
    p = Prg()
    p.i = I(size=size)
    p.x, p.y = V(p.i), V(p.i)
    p.k = P(p.i, _=list(range(1, size + 1)))
    p.t = T(p.i, _=(-2, 3))
    return p


def constraint(p, kind):
    """Cover relations, repeated terms, theta columns and reduction rows."""
    bound = 20
    choices = {
        "binary": lambda: p.k * p.x + 3 <= bound,
        "equality": lambda: p.x + p.y == bound,
        "repeated": lambda: p.x + p.x - p.y <= bound,
        "theta": lambda: p.k * p.x - p.t + 3 <= bound,
        "anonymous": lambda: p.x <= T(p.i, _=(0, 5)),
        "negative": lambda: p.x >= 0,
        "reduction": lambda: sigma(p.k * p.x) <= bound,
    }
    return choices[kind]()


def signature(row):
    """Compare public scalar data without asking for full membership maps."""
    return (
        repr(row.index),
        row.pos,
        row.n,
        row.category,
        row.leq,
        row.nn,
        row.args,
        row.A,
        row.P,
        row.B,
        row.F,
        row.Z,
        str(row),
        row.latex(),
        row.longname,
    )


@pytest.mark.parametrize(
    "kind",
    [
        "binary",
        "equality",
        "repeated",
        "theta",
        "anonymous",
        "negative",
        "reduction",
    ],
)
@pytest.mark.parametrize("position", [0, -1])
def test_projected_constraint_matches_legacy(kind, position):
    """Projection matches the original compiler without expanding siblings."""
    p, reference = model(), model()
    p.c = constraint(p, kind)
    reference.c = constraint(reference, kind)
    # The original compatibility builder is an independent projection oracle.
    reference.c._materialize()
    row = p.c[position]
    CHECK.assertEqual(signature(row), signature(reference.c[position]))
    CHECK.assertIs(row.parent, p.c)
    CHECK.assertIs(row.function, p.c.function[position])
    CHECK.assertIs(p.constraints[position], row)
    CHECK.assertNotIn("_legacy_cache", p.c.__dict__)
    CHECK.assertNotIn("_legacy_cache", p.c.function.__dict__)
    CHECK.assertEqual(len(p.c._native_rows), 1)
    CHECK.assertIsNotNone(compile_program(p))


def test_slices_and_partial_iteration_keep_requested_identities():
    """Slices share rows; an unconsumed iterator creates no rows."""
    p = model()
    p.c = constraint(p, "binary")
    iterator = iter(p.c)
    CHECK.assertNotIn("_native_rows", p.c.__dict__)
    first = next(iterator)
    CHECK.assertEqual(len(p.c._native_rows), 1)
    selected = p.c[-1::-5]
    CHECK.assertEqual([row.pos for row in selected], [11, 6, 1])
    CHECK.assertIs(first, p.c[0])
    CHECK.assertEqual(len(p.c._native_rows), 4)
    CHECK.assertNotIn("_legacy_cache", p.c.__dict__)
    with pytest.raises(IndexError):
        _ = p.c[len(p.c)]


@pytest.mark.parametrize(
    "field",
    ["coefficient", "relation", "args", "variables"],
)
def test_first_edit_preserves_rows_and_invalidates_native_compilation(field):
    """Function and constraint edits preserve escaped aliases."""
    p = model(3)
    p.c = constraint(p, "binary")
    row = p.c[0]
    function, coefficients, members = row.function, row.A, row._
    if field == "coefficient":
        coefficients[0] = 9
    elif field == "relation":
        row.leq = False
    elif field == "args":
        row.args["nn"] = True
    else:
        row.variables = list(row.variables)
    CHECK.assertIsNone(compile_program(p))
    CHECK.assertIs(p.c._[0], row)
    CHECK.assertIs(row.function, function)
    CHECK.assertIs(row.A, coefficients)
    CHECK.assertIs(row._, members)
    CHECK.assertIs(members[0], row)
    if field == "coefficient":
        CHECK.assertEqual(p.A[0][0], 9)


def test_membership_read_replays_in_order_and_preserves_exposed_rows():
    """Older overlapping batches precede a projected later constraint."""
    p = model(3)
    first_bound, middle_bound, last_bound = 8, 9, 10
    p.first = 2 * p.y <= first_bound
    p.middle = p.x + p.y <= middle_bound
    p.last = 3 * p.x <= last_bound
    middle, last = p.middle[0], p.last[0]
    x, y = p.x[0], p.y[0]
    CHECK.assertEqual(middle.cons_by_pos[x], 0)
    CHECK.assertEqual([id(row) for row in x.cons_by], [id(middle), id(last)])
    CHECK.assertEqual(
        [id(row) for row in y.cons_by],
        [id(p.first[0]), id(middle)],
    )
    for variable in (x, y):
        for position, row in enumerate(variable.cons_by):
            CHECK.assertEqual(row.cons_by_pos[variable], position)


def test_category_and_export_numbering_update_live_projected_rows():
    """Owner metadata updates do not force coefficient or membership replay."""
    p = model(2)
    equal_bound, upper_bound = 5, 7
    p.eq = 2 * p.x == equal_bound
    p.c = 3 * p.y <= upper_bound
    equality, inequality = p.eq[0], p.c[0]
    CHECK.assertEqual((equality.n, inequality.n), (0, 2))
    p.c.categorize("Capacity")
    CHECK.assertEqual(inequality.category, "Capacity")
    renumber(p)
    CHECK.assertEqual((equality.n, inequality.n), (2, 0))
    CHECK.assertNotIn("_legacy_cache", p.c.__dict__)


def test_registration_after_projection_binds_rows_and_preserves_identity():
    """Reading a declaration before registration retains normal bookkeeping."""
    p = model(2)
    source = constraint(p, "anonymous")
    row = source[0]
    CHECK.assertIsNone(row.n)
    p.c = source
    CHECK.assertIs(p.c[0], row)
    CHECK.assertEqual(row.n, 0)
    CHECK.assertEqual(row.Z, [len(p.t)])
    CHECK.assertIs(p.x[0].cons_by[0], row)


@pytest.mark.parametrize(
    "clone",
    [deepcopy, lambda value: pickle.loads(pickle.dumps(value))],
)
def test_copy_after_row_read_keeps_one_copied_graph(clone):
    """A copied program reuses its own rows and variable membership lists."""
    p = model(2)
    p.c = constraint(p, "theta")
    original = p.c[0]
    # The pickle roundtrip consumes only bytes created from this local fixture.
    copied = clone(p)
    CHECK.assertIs(p.c[0], original)
    CHECK.assertIsNot(copied.c[0], original)
    CHECK.assertIs(copied.x[0].cons_by[0], copied.c[0])
    CHECK.assertIs(copied.c[0].function, copied.c.function[0])
    CHECK.assertEqual(copied.A, p.A)
    CHECK.assertEqual(copied.F, p.F)


@pytest.mark.parametrize("name", ["F", "Z"])
def test_escaped_theta_array_is_preserved_across_function_edits(name):
    """Promotion restores bound columns before an escaped array is mutated."""
    p = model(3)
    p.c = constraint(p, "theta")
    row = p.c[0]
    array = getattr(row.function, name)
    replacement = 2
    array[0] = replacement
    CHECK.assertIs(getattr(row.function, name), array)
    CHECK.assertIs(getattr(p.c.function, name)[0], array)
    CHECK.assertIs(p.c[0], row)
    CHECK.assertEqual(array[0], replacement)
    CHECK.assertIsNone(compile_program(p))


def test_function_field_replacement_keeps_edited_theta_coefficients():
    """Scalar assignments finish constraint binding before editing."""
    p = model(3)
    p.c = constraint(p, "theta")
    row = p.c[0]
    row.function.F = [9]
    CHECK.assertIs(p.c._[0], row)
    CHECK.assertEqual(row.F, [9])
    CHECK.assertEqual(p.F[0], [9, 0, 0])


def test_iterator_observes_legacy_list_growth_after_promotion():
    """Switching representations keeps the original list iterator contract."""
    p = model(2)
    p.c = constraint(p, "binary")
    iterator = iter(p.c)
    first = next(iterator)
    p.c._.append(first)
    CHECK.assertEqual([id(row) for row in iterator], [id(p.c[1]), id(first)])


def test_display_protocol_probes_leave_constraint_lazy():
    """Notebook introspection must not accidentally request all scalar rows."""
    p = model(2)
    p.c = constraint(p, "binary")
    CHECK.assertFalse(hasattr(p.c, "_repr_mimebundle_"))
    CHECK.assertFalse(hasattr(p.c, "_ipython_display_"))
    CHECK.assertNotIn("_legacy_cache", p.c.__dict__)
    CHECK.assertIsInstance(p.c[0], C)
