"""Independent invariants for updates, selection and program ownership."""

import gc
import pickle
import weakref
from unittest import TestCase
from warnings import catch_warnings, simplefilter

import numpy as np
import pytest

from src.gana import I, P, Prg, T, V, inf, sigma
from src.gana.sets.cases import PCase

CHECK = TestCase()


def model():
    """
    Build overlapping named domains with distinct numeric values and bounds.
    """
    p = Prg()
    p.i = I("a", "b")
    p.j = I("b", "c")
    p.k = I("c", "d")
    p.x = V(p.i, mutable=True)
    p.data = P(p.i, _=[2, 3], mutable=True)
    p.t = T(p.i, _=[(0, 2), (1, 3)], mutable=True)
    return p


def declarations(p):
    """Retain compared objects so identity checks span live wrapper lifetimes.

    Compare IDs first to avoid symbolic equality when membership changes.
    Keeping each object also prevents collection and address reuse between
    snapshots when the native registry uses a weak scalar-wrapper cache.
    """
    return (
        tuple(p.names),
        tuple((id(member), member) for member in p.variables),
        tuple((id(member), member) for member in p.thetas),
        p.n_variables,
        p.n_thetas,
        p.n_parameter_sets,
    )


def test_parameter_replacement_and_growth():
    """
    Overwrite in place by coordinate, append new keys, and retain snapshots.
    """
    p = model()
    root, selected, values = p.data, p.data(p.a), p.data[:]
    p.o = inf(sigma(p.data * p.x))
    with pytest.warns(UserWarning, match="overwritten"):
        p.data = P(p.i, _=[7, 9])
    CHECK.assertIs(p.data, root)
    np.testing.assert_array_equal(p.data._, [7, 9])
    np.testing.assert_array_equal(list(p.data.map.values()), [7, 9])
    np.testing.assert_array_equal(selected._, [2])
    np.testing.assert_array_equal(values, [2, 3])
    np.testing.assert_array_equal(p.C, [2, 3])
    with pytest.warns(UserWarning, match="overwritten"):
        p.data = P(p.j, _=[11, 13])
    with pytest.warns(UserWarning, match="overwritten"):
        p.data = P(p.k, _=[17, 19])
    np.testing.assert_array_equal(p.data._, [7, 11, 17, 19])
    np.testing.assert_array_equal(list(p.data.map.values()), p.data._)
    CHECK.assertEqual(
        [key[0].name for key in p.data.map],
        ["a", "b", "c", "d"],
    )
    np.testing.assert_array_equal(p.data(p.c)._, [17])


def test_parameter_warning_failure_is_atomic():
    """
    Warning-as-error must abort before the first replacement is committed.
    """
    p = model()
    before = declarations(p)
    with catch_warnings():
        simplefilter("error", UserWarning)
        with pytest.raises(UserWarning):
            p.data = P(p.j, _=[7, 9])
    CHECK.assertEqual(declarations(p), before)
    np.testing.assert_array_equal(p.data._, [2, 3])
    np.testing.assert_array_equal(list(p.data.map.values()), [2, 3])


@pytest.mark.parametrize("damage", ["length", "map", "value"])
def test_invalid_parameter_update_is_atomic(damage):
    """
    Reject inconsistent legacy raw buffers before touching the registered root.
    """
    p = model()
    incoming = P(p.j, _=[7, 9])
    if damage == "length":
        incoming._.pop()
    elif damage == "map":
        incoming.map[(p.b,)] = 100
    else:
        incoming._[0] = "invalid"
        incoming.map[(p.b,)] = "invalid"
    before = declarations(p)
    with pytest.raises((ValueError, TypeError)):
        p.data = incoming
    CHECK.assertEqual(declarations(p), before)
    np.testing.assert_array_equal(p.data._, [2, 3])
    np.testing.assert_array_equal(list(p.data.map.values()), [2, 3])


@pytest.mark.parametrize("kind", [V, T])
def test_overlapping_growth_allocates_only_accepted_ids(kind):
    """
    Overlap and a third splice retain original identities and unique global
    IDs.
    """
    p = model()
    name = "x" if kind is V else "t"
    root = getattr(p, name)
    selected = root(p.a)
    first, second = root[0], root[1]
    args = {} if kind is V else {"_": [(10, 20), (30, 40)]}
    setattr(p, name, kind(p.j, **args))
    setattr(p, name, kind(p.k, **args))
    p.extra = kind(p.a, **({} if kind is V else {"_": [(50, 60)]}))
    members = p.variables if kind is V else p.thetas
    CHECK.assertEqual([v.n for v in members], list(range(5)))
    CHECK.assertEqual([v.pos for v in root], list(range(4)))
    CHECK.assertIs(root[0], first)
    CHECK.assertIs(root[1], second)
    CHECK.assertIs(selected[0], first)
    CHECK.assertEqual(len(selected), 1)
    CHECK.assertEqual([key[0].name for key in root.map], ["a", "b", "c", "d"])
    CHECK.assertIs(root(p.d)[0], root[3])
    CHECK.assertTrue(all(v.parent is root for v in root))
    if kind is T:
        CHECK.assertEqual(
            [(t.lb, t.ub) for t in root],
            [(0, 2), (1, 3), (30, 40), (30, 40)],
        )


def test_growth_exports_and_loads_the_correct_columns(tmp_path, monkeypatch):
    """MPS read-back distinguishes all newly appended columns numerically."""
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = model()
    p.x = V(p.j)
    p.extra = V(p.a)
    p.fixed = p.x == [2, 3, 4]
    extra_value = 5
    p.fixed_extra = p.extra == extra_value
    p.o = inf(sigma(p.x) + p.extra)
    p.mps(name="growth")
    with gp.read("growth.mps") as parsed:
        np.testing.assert_array_equal(parsed.getA().toarray(), np.eye(4))
        np.testing.assert_array_equal(parsed.getAttr("RHS"), [2, 3, 4, 5])
    p._load_values(({"V0": 2, "V1": 3, "V2": 4, "V3": 5}, 14))
    np.testing.assert_array_equal(p.X[0], [2, 3, 4, 5])


def test_domain_change_is_rejected_before_growth():
    """A homogeneous variable owner cannot silently acquire another domain."""
    p = model()
    before = declarations(p)
    with pytest.raises(ValueError, match="domain"):
        p.x = V(p.j, bnr=True)
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertEqual(len(p.x), 2)


def test_theta_selection_and_bounds():
    """
    Partial selections share actual theta members and produce exact RHS
    columns.
    """
    p = model()
    selected = p.t(p.b)
    CHECK.assertIs(selected[0], p.t[1])
    CHECK.assertIs(selected.map[(p.b,)], p.t[1])
    p.row = p.x(p.a) <= selected
    np.testing.assert_array_equal(p.A, [[1, 0]])
    np.testing.assert_array_equal(p.F, [[0, 1]])
    np.testing.assert_array_equal(selected.CrB, [3, -1])
    with pytest.raises(KeyError):
        p.t(p.d)


@pytest.mark.parametrize("kind", [P, V, T])
def test_scalar_registration(kind):
    """
    Indexless scalar payloads receive one real coordinate and one registration.
    """
    p = Prg()
    args = {P: {"_": 2}, V: {}, T: {"_": (0, 2)}}[kind]
    root = kind(**args)
    p.e = root
    CHECK.assertIs(p.e, root)
    CHECK.assertEqual(len(root), 1)
    CHECK.assertEqual(len(root.map), 1)
    CHECK.assertEqual(len(root._), 1)
    if kind is P:
        CHECK.assertEqual((p.n_parameter_sets, root.n, root[0]), (1, 0, 2))
    else:
        CHECK.assertIs(next(iter(root.map.values())), root[0])
        CHECK.assertIs(root[0].parent, root)


@pytest.mark.parametrize("kind", [P, V, T])
def test_same_program_alias_and_reassignment(kind):
    """
    Aliases and exact self-assignment neither rebirth nor duplicate
    registrations.
    """
    p = model()
    name = {P: "data", V: "x", T: "t"}[kind]
    root = getattr(p, name)
    before = declarations(p)
    setattr(p, name, root)
    p.alias = root
    p.selected = root(p.a)
    CHECK.assertIs(p.alias, root)
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertEqual(len(root), 2)
    if kind is not P:
        CHECK.assertIs(p.selected[0], root[0])


@pytest.mark.parametrize("kind", [P, V, T])
@pytest.mark.parametrize("selection", [False, True])
def test_foreign_registration_is_atomic(kind, selection):
    """
    Foreign roots and selections are rejected without changing either model.
    """
    p, q = model(), Prg()
    root = getattr(p, {P: "data", V: "x", T: "t"}[kind])
    value = root(p.a) if selection else root
    before_p, before_q = declarations(p), declarations(q)
    with pytest.raises(ValueError, match="another program"):
        q.foreign = value
    CHECK.assertEqual(declarations(p), before_p)
    CHECK.assertEqual(declarations(q), before_q)
    CHECK.assertFalse(hasattr(q, "foreign"))
    CHECK.assertEqual(len(root), 2)


@pytest.mark.parametrize("kind", [P, V, T])
def test_ownership_does_not_keep_program_alive(kind):
    """
    A surviving owner keeps data, not the program; a dead binding stays
    foreign.
    """
    p = model()
    root = getattr(p, {P: "data", V: "x", T: "t"}[kind])
    reference = weakref.ref(p)
    del p
    gc.collect()
    CHECK.assertIsNone(reference())
    with pytest.raises(ValueError, match="another program"):
        Prg().foreign = root


def test_program_pickle_preserves_ownership():
    """Ownership metadata must serialize without retaining a Python weakref."""
    p = pickle.loads(pickle.dumps(model()))
    before = declarations(p)
    p.alias = p.x
    CHECK.assertEqual(declarations(p), before)
    with pytest.raises(ValueError, match="another program"):
        Prg().foreign = p.x


@pytest.mark.parametrize("kind", [P, T])
def test_invalid_payload_does_not_register(kind):
    """
    Reject a malformed declaration before program names or counters change.
    """
    p = model()
    before = declarations(p)
    args = {P: {"_": [1]}, T: {"_": [(0, 1)]}}[kind]
    with pytest.raises(ValueError, match=r"length|bounds|values"):
        p.bad = kind(p.i, **args)
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertFalse(hasattr(p, "bad"))


@pytest.mark.parametrize("kind", [P, V, T])
def test_immutable_owner_can_be_aliased(kind):
    """Self assignment and aliases do not request mutation permission."""
    p = Prg()
    args = {P: {"_": 2}, V: {}, T: {"_": (0, 2)}}[kind]
    p.owner = kind(**args)
    root, before = p.owner, declarations(p)
    p.owner = root
    p.alias = root
    CHECK.assertIs(p.alias, root)
    CHECK.assertEqual(declarations(p), before)
    with pytest.raises(ValueError, match="mutable"):
        p.owner = kind(**args)
    CHECK.assertEqual(declarations(p), before)


@pytest.mark.parametrize("kind", [P, V, T])
def test_selection_alias_cannot_mutate_its_root(kind):
    """
    A view must not silently become an independent owner during assignment.
    """
    p = model()
    root = getattr(p, {P: "data", V: "x", T: "t"}[kind])
    p.view = root(p.a)
    before = declarations(p)
    args = {P: {"_": [7]}, V: {}, T: {"_": [(0, 7)]}}[kind]
    with pytest.raises(ValueError, match="selection"):
        p.view = kind(p.a, **args)
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertEqual(len(root), 2)


@pytest.mark.parametrize("kind", [P, V, T])
def test_registered_update_source_is_rejected(kind):
    """Updating from another owner must not steal or renumber its members."""
    p = model()
    name = {P: "data", V: "x", T: "t"}[kind]
    args = {P: {"_": [7]}, V: {}, T: {"_": [(0, 7)]}}[kind]
    p.other = kind(p.c, **args)
    before = declarations(p)
    with pytest.raises(ValueError, match="fresh"):
        setattr(p, name, p.other)
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertEqual(len(getattr(p, name)), 2)


@pytest.mark.parametrize("kind", [P, V, T])
def test_direct_registration_reuses_binding(kind):
    """Explicit add methods enforce the same binding rules as attributes."""
    p, q = model(), Prg()
    root = getattr(p, {P: "data", V: "x", T: "t"}[kind])
    method = {P: "add_parameter", V: "add_variable", T: "add_theta"}[kind]
    before = declarations(p)
    getattr(p, method)("again", root)
    CHECK.assertEqual(declarations(p), before)
    with pytest.raises(ValueError, match="another program"):
        getattr(q, method)("foreign", root)
    CHECK.assertEqual(declarations(q), declarations(Prg()))


@pytest.mark.parametrize(
    "operation",
    ["function", "constraint", "objective", "theta"],
)
def test_foreign_expression_does_not_change_bookkeeping(operation):
    """Foreign columns and theta IDs must never enter a second program."""
    p, q = model(), model()
    if operation == "theta":
        value = q.x <= p.t
    elif operation == "function":
        value = 2 * p.x
    elif operation == "constraint":
        bound = 4
        value = p.x <= bound
    else:
        value = inf(sigma(p.x))
    before_p, before_q = declarations(p), declarations(q)
    with pytest.raises(ValueError, match="another program"):
        q.foreign = value
    CHECK.assertEqual(declarations(p), before_p)
    CHECK.assertEqual(declarations(q), before_q)
    CHECK.assertEqual(
        (q.n_function_sets, q.n_constraints, q.n_objectives),
        (0, 0, 0),
    )
    CHECK.assertFalse(hasattr(q, "foreign"))


def test_scalar_parameter_replacement_refreshes_numeric_shortcuts():
    """
    Sign changes update new expressions while earlier coefficients stay fixed.
    """
    p = Prg()
    p.rate = P(_=2, mutable=True, ltx="rate")
    p.x = V()
    p.o = inf(p.rate * p.x)
    with pytest.warns(UserWarning):
        p.rate = P(_=-3)
    np.testing.assert_array_equal(p.C, [2])
    p.o = inf(p.rate * p.x)
    np.testing.assert_array_equal(p.C, [-3])
    CHECK.assertEqual(p.rate._ltx, "rate")


@pytest.mark.parametrize(
    "bounds",
    [[(2, 1), (0, 4)], [(0, float("nan")), (0, 4)], [(0, 4)]],
)
def test_invalid_theta_growth_is_atomic(bounds):
    """
    Validate every interval before changing bounds, membership or counters.
    """
    p = model()
    before = declarations(p)
    with pytest.raises(ValueError, match="bounds"):
        p.t = T(p.j, _=bounds)
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertEqual([(t.lb, t.ub) for t in p.t], [(0, 2), (1, 3)])


def test_two_dimensional_theta_selection():
    """
    Product selections retain coordinates, member identity and bounds order.
    """
    p = model()
    p.grid = T(p.i, p.k, _=[(0, 2), (1, 3), (2, 4), (3, 5)])
    selected = p.grid(p.b, p.k)
    CHECK.assertEqual(list(selected.map), [(p.b, p.c), (p.b, p.d)])
    CHECK.assertIs(selected[0], p.grid[2])
    CHECK.assertIs(selected[1], p.grid[3])
    CHECK.assertEqual(selected.CrB, [4, -2, 5, -3])


def test_scalar_theta_compilation():
    """
    Scalar declarations compile to one variable column and one theta column.
    """
    p = Prg()
    p.x = V()
    p.t = T(_=(1, 4))
    p.row = p.x <= p.t
    p.o = inf(p.x)
    np.testing.assert_array_equal(p.A, [[1]])
    np.testing.assert_array_equal(p.F, [[1]])
    np.testing.assert_array_equal(p.C, [1])
    CHECK.assertEqual(p.CrB, [4, -1])


def test_fully_overlapping_growth_is_noop():
    """Duplicate coordinates do not consume IDs or change existing bounds."""
    p = model()
    before = declarations(p)
    p.x = V(p.i)
    p.t = T(p.i, _=[(100, 200), (300, 400)])
    CHECK.assertEqual(declarations(p), before)
    CHECK.assertEqual([(t.lb, t.ub) for t in p.t], [(0, 2), (1, 3)])


def test_indexless_parameter_update_matches_positions():
    """
    Fresh implicit coordinates replace earlier positions before appending.
    """
    p = Prg()
    p.data = P(_=[2, 3], mutable=True)
    original_keys = list(p.data.map)
    with pytest.warns(UserWarning):
        p.data = P(_=[7, 11, 13])
    CHECK.assertEqual(list(p.data.map)[:2], original_keys)
    np.testing.assert_array_equal(p.data._, [7, 11, 13])
    np.testing.assert_array_equal(list(p.data.map.values()), [7, 11, 13])


@pytest.mark.parametrize("kind", [P, V, T])
def test_explicit_empty_domain_registers_no_members(kind):
    """
    An explicitly empty domain must remain empty instead of becoming scalar.
    """
    p = Prg()
    p.i = I()
    args = {P: {"_": []}, V: {}, T: {"_": []}}[kind]
    p.empty = kind(p.i, **args)
    CHECK.assertEqual(len(p.empty), 0)
    CHECK.assertEqual(p.empty.map, {})
    CHECK.assertEqual((p.n_variables, p.n_thetas), (0, 0))


def test_nan_parameter_is_not_simplified_to_zero():
    """
    Preserve non-finite numeric payloads instead of selecting the zero
    shortcut.
    """
    p = Prg()
    p.data = P(_=float("nan"))
    CHECK.assertIs(p.data.case, PCase.NUM)
    np.testing.assert_equal(np.isnan(p.data[0]), True)


class LazyProgram(Prg):
    """
    Detect registration probes that would activate a frontend's lazy factory.
    """

    def __getattr__(self, name):
        """
        Fail immediately instead of recursing through automatic index creation.
        """
        message = f"Registration queried an absent attribute: {name}"
        raise AssertionError(message)


def test_registration_does_not_activate_lazy_attributes():
    """
    Adding indices and P/V/T must inspect stored attributes without
    __getattr__.
    """
    p = LazyProgram()
    p.i = I("a", "b")
    p.x = V(p.i)
    p.data = P(p.i, _=[2, 3])
    p.t = T(p.i, _=[(0, 2), (1, 3)])
    CHECK.assertEqual(
        (p.n_variables, p.n_parameter_sets, p.n_thetas),
        (2, 1, 2),
    )
    p.alias = p.x
    CHECK.assertIs(p.alias, p.x)


@pytest.mark.parametrize(
    ("lower", "upper"),
    [
        (2**53 + 1, 2**53 + 3),
        (np.int64(2**53 + 1), np.int64(2**53 + 3)),
        (np.float64(1.5), np.float64(3.5)),
    ],
)
def test_theta_bounds_preserve_supplied_numbers(lower, upper):
    """
    Keep integer precision and NumPy numeric values when validating intervals.
    """
    p = Prg()
    p.i = I(size=1)
    p.t = T(p.i, _=[(lower, upper)])
    CHECK.assertEqual(int(p.t[0].lb), int(lower))
    CHECK.assertEqual(int(p.t[0].ub), int(upper))
    CHECK.assertEqual((p.t[0].lb, p.t[0].ub), (lower, upper))
