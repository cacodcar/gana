"""
Native symbolic ownership, lazy identity, exact intervals and serialization.
"""

import gc
import pickle
import weakref
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V, inf, sigma
from gana.storage import parameters as storage
from gana.storage.parameters import NATIVE

CHECK = TestCase()
pytestmark = pytest.mark.skipif(not NATIVE, reason="requires native owners")


@pytest.mark.parametrize("kind", [V, T])
def test_python_growth_after_restoring_a_native_registry(kind, monkeypatch):
    """
    A saved registry accepts new Python owners and their subsequent growth.
    """
    p = Prg()
    p.i, p.j = I("a", "b"), I("c")
    args = {"_": (0, 2)} if kind is T else {}
    p.native = kind(p.i, **args)
    monkeypatch.setattr(storage, "NATIVE", False)
    p.legacy = kind(p.i, mutable=True, **args)
    p.legacy = kind(p.j, **args)
    registry = p.variables if kind is V else p.thetas
    CHECK.assertEqual([member.n for member in registry], [0, 1, 2, 3, 4])
    CHECK.assertEqual(len(p.legacy), 3)


@pytest.mark.parametrize("kind", [V, T])
def test_registration_selection_growth_are_lazy(kind):
    """
    Large root/selection construction must not silently fill scalar wrappers.
    """
    p = Prg()
    p.i, p.j = I(size=1000), I("extra")
    args = {"_": (0, 2)} if kind is T else {}
    p.x = kind(p.i, mutable=True, **args)
    selected = p.x(p.i[::2])
    values, mapping = p.x._, p.x.map
    p.x = kind(p.j, **args)
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertEqual(len(values), 1001)
    CHECK.assertEqual(len(mapping), 1001)
    CHECK.assertEqual(len(selected), 500)
    first = selected[0]
    CHECK.assertIs(first, p.x[0])
    CHECK.assertIs(first, mapping[first.index])
    CHECK.assertEqual(first.n, 0)


@pytest.mark.parametrize("kind", [V, T])
def test_wrappers_collect_but_member_state_survives(kind):
    """
    Weak identity caches must preserve state and never keep a program alive.
    """
    p = Prg()
    p.i = I("a", "b")
    p.x = kind(p.i, **({"_": (0, 2)} if kind is T else {}))
    member = p.x[0]
    member.tag = "retained metadata"
    if kind is V:
        member.X[3] = 42
    reference, program = weakref.ref(member), weakref.ref(p)
    selected = p.x(p.a)
    del member
    gc.collect()
    CHECK.assertIsNone(reference())
    CHECK.assertEqual(selected[0].tag, "retained metadata")
    if kind is V:
        CHECK.assertEqual(selected[0].X, {3: 42})
    root = weakref.ref(p.x)
    del p
    gc.collect()
    CHECK.assertIsNone(program())
    CHECK.assertIs(selected[0].parent, root())
    del selected
    gc.collect()
    CHECK.assertIsNone(root())


def test_interleaved_growth_preserves_global_column_order():
    """
    Global order follows registration events rather than grouping growing
    roots.
    """
    p = Prg()
    p.i, p.j = I("a", "b"), I("c", "d")
    p.x, p.y = V(p.i, mutable=True), V(p.i)
    held = p.x[1]
    p.x = V(p.j)
    CHECK.assertEqual([v.n for v in p.variables], list(range(6)))
    CHECK.assertEqual(
        [v.name for v in p.variables],
        ["x[0]", "x[1]", "y[0]", "y[1]", "x[2]", "x[3]"],
    )
    CHECK.assertIs(p.variables[1], held)
    p.o = inf(sigma(2 * p.x) + sigma(3 * p.y))
    CHECK.assertEqual(p.C, [2, 2, 3, 3, 2, 2])


def test_exact_theta_bounds_and_atomic_invalid_growth():
    """
    Large endpoints retain exact integers through views, growth and pickle.
    """
    p = Prg()
    p.i, p.j = I("a"), I("b")
    large = 2**80 + 1
    p.t = T(p.i, _=(large, large + 2), mutable=True)
    selected = p.t(p.i)
    CHECK.assertEqual((selected[0].lb, selected[0].ub), (large, large + 2))
    selected[0].ub = large + 4
    p.t = T(p.j, _=(-large, -large + 3))
    restored = pickle.loads(pickle.dumps(p))
    CHECK.assertEqual(
        [(t.lb, t.ub) for t in restored.t],
        [(large, large + 4), (-large, -large + 3)],
    )
    with pytest.raises(ValueError):
        restored.t[0].ub = large - 1
    CHECK.assertEqual(restored.t[0].ub, large + 4)


@pytest.mark.parametrize("kind", [V, T])
def test_raw_symbol_replacement_is_rejected(kind):
    """
    Neither facade nor root container replacement may change native identity.
    """
    p = Prg()
    p.i = I("a")
    p.x = kind(p.i, **({"_": (0, 2)} if kind is T else {}))
    first = p.x[0]
    with pytest.raises(TypeError, match="program reassignment"):
        p.x._[0] = None
    with pytest.raises(TypeError, match="program reassignment"):
        p.x.map[(p.a,)] = None
    with pytest.raises(TypeError, match="program reassignment"):
        p.x._ = []
    for attribute in ("n", "pos", "parent"):
        with pytest.raises(TypeError, match="program reassignment"):
            setattr(first, attribute, None)
    CHECK.assertIs(p.x[0], first)


def test_pickle_reuses_members_already_captured_by_expressions():
    """
    Restored expressions, registries and selections must share scalar
    identities.
    """
    p = Prg()
    p.i = I("a", "b")
    p.x = V(p.i, mutable=True)
    p.k = P(p.i, _=[2, 3])
    p.o = inf(sigma(p.k * p.x))
    restored = pickle.loads(pickle.dumps(p))
    CHECK.assertEqual(restored.C, [2, 3])
    CHECK.assertIs(restored.x[0], restored.variables[0])
    CHECK.assertIs(restored.x[0], restored.active_objective.variables[0])


@pytest.mark.parametrize("kind", [P, V, T])
def test_mapping_preserves_noncoordinate_key_errors(kind):
    """
    Tuple coordinates must not accidentally accept scalar or list spellings.
    """
    p = Prg()
    p.i = I("a")
    args = {P: {"_": [1]}, V: {}, T: {"_": (0, 2)}}[kind]
    p.e = kind(p.i, **args)
    for key in (1, p.a, "a", ("missing",)):
        with pytest.raises(KeyError):
            p.e.map[key]
    with pytest.raises(TypeError):
        p.e.map[[p.a]]


@pytest.mark.parametrize("kind", [V, T])
def test_retained_mapping_items_view_tracks_root_growth(kind):
    """
    Creating a mapping view does not freeze its membership or fill wrappers.
    """
    p = Prg()
    p.i, p.j = I("a"), I("b")
    args = {"_": (0, 2)} if kind is T else {}
    p.e = kind(p.i, mutable=True, **args)
    items = p.e.map.items()
    p.e = kind(p.j, **args)
    CHECK.assertEqual(p.e._symbol_storage.states, {})
    CHECK.assertEqual([member.n for _, member in items], [0, 1])
