"""Supported Python ownership behavior that native handles must preserve."""

import gc
import weakref
from unittest import TestCase

import numpy as np
import pytest

from src.gana import I, P, Prg, T, V, inf, sigma

CHECK = TestCase()


def model():
    """Build a small model with distinct coordinates and mutable variables."""
    p = Prg()
    p.i = I("a", "b")
    p.j = I("c")
    p.x = V(p.i, mutable=True)
    p.k = P(p.i, _=[2, 3])
    p.t = T(p.i, _=[(0, 2), (1, 3)])
    return p


def test_growth_preserves_existing_members_and_selections():
    """
    Root aliases grow; previously made selection containers retain membership.
    """
    p = model()
    root, selected, copied = p.x(), p.x(p.a), p.x.copy()
    forced = p.x(p.i, make_new=True)
    first, second = p.x[0], p.x[1]
    p.o = inf(sigma(2 * p.x))
    p.x = V(p.j)
    CHECK.assertIs(root, p.x)
    CHECK.assertEqual(
        [len(root), len(selected), len(copied), len(forced)],
        [3, 1, 2, 2],
    )
    CHECK.assertIs(selected[0], first)
    CHECK.assertIs(copied[1], second)
    CHECK.assertIs(forced[1], second)
    CHECK.assertIs(first.parent, root)
    np.testing.assert_array_equal(p.C, [2, 2, 0])


def test_selection_keeps_owner_alive_and_can_be_reclaimed():
    """
    A retained scalar has a valid parent after program deletion; cycles
    collect.
    """
    p = model()
    selected = p.x(p.a)
    owner = weakref.ref(p.x)
    program = weakref.ref(p)
    del p
    gc.collect()
    CHECK.assertIsNone(program())
    CHECK.assertIs(selected[0].parent, owner())
    CHECK.assertIsNotNone(owner())
    del selected
    gc.collect()
    CHECK.assertIsNone(owner())


def test_numeric_selection_is_a_snapshot():
    """
    Selections and captured coefficients retain their original numeric values.
    """
    p = model()
    selected, values = p.k(p.a), p.k[:]
    p.o = inf(sigma(p.k * p.x))
    # This probe describes current storage; it does not bless raw writes as
    # the future native mutation API. Both legacy buffers must be kept aligned.
    p.k._[0] = 9
    p.k.map[(p.a,)] = 9
    np.testing.assert_array_equal(selected._, [2])
    np.testing.assert_array_equal(values, [2, 3])
    np.testing.assert_array_equal(p.k(p.a)._, [9])
    np.testing.assert_array_equal(p.C, [2, 3])


def test_registration_retains_root_identity():
    """Initial variable registration populates the original root object."""
    p = Prg()
    p.i = I(size=2)
    root = V(p.i)
    CHECK.assertEqual(len(root), 0)
    p.x = root
    CHECK.assertIs(p.x, root)
    CHECK.assertEqual(len(root), 2)
    CHECK.assertIs(root[0].parent, root)


@pytest.mark.parametrize("kind", [P, V, T])
def test_immutable_reassignment_leaves_original_untouched(kind):
    """Default immutability rejects replacement before altering the owner."""
    p = Prg()
    p.i = I(size=1)
    arguments = {P: {"_": [2]}, V: {}, T: {"_": [(0, 2)]}}[kind]
    p.e = kind(p.i, **arguments)
    root = p.e
    members = list(root)
    with pytest.raises(ValueError, match="mutable=True"):
        p.e = kind(p.i, **arguments)
    CHECK.assertIs(p.e, root)
    CHECK.assertEqual(len(root), len(members))
    if kind is P:
        CHECK.assertEqual(root[0], members[0])
    else:
        CHECK.assertIs(root[0], members[0])
