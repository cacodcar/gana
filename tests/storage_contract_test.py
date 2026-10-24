"""Legacy container lifetimes required by the native compatibility adapter."""

from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf

CHECK = TestCase()


@pytest.mark.parametrize("kind", [V, T])
def test_members_keep_metadata_from_their_registration_span(kind):
    """Lazy access must not make member metadata depend on later root edits."""
    p = Prg()
    p.i, p.j = I("a"), I("b")
    args = {"_": (0, 2)} if kind is T else {}
    p.e = kind(p.i, tag="original", mutable=True, **args)
    p.e.name, p.e.tag = "renamed", "updated"
    p.e = kind(p.j, **args)
    CHECK.assertEqual([member.name for member in p.e], ["e[0]", "renamed[1]"])
    CHECK.assertEqual([member.tag for member in p.e], ["original", "updated"])


def test_parameter_replacement_detaches_retained_raw_containers():
    """A P update replaces storage; previously retained buffers stay old."""
    p = Prg()
    p.i = I("a", "b")
    p.k = P(p.i, _=[2, 3], mutable=True)
    values, mapping = p.k._, p.k.map
    with pytest.warns(UserWarning):
        p.k = P(p.i, _=[4, 5])
    np.testing.assert_array_equal(values, [2, 3])
    np.testing.assert_array_equal(list(mapping.values()), [2, 3])
    values[0] = mapping[(p.a,)] = 99
    np.testing.assert_array_equal(p.k._, [4, 5])
    np.testing.assert_array_equal(list(p.k.map.values()), [4, 5])


@pytest.mark.parametrize("kind", [V, T])
def test_symbolic_growth_keeps_retained_raw_containers_live(kind):
    """V/T grow root containers in place; partial selections stay fixed."""
    p = Prg()
    p.i, p.j = I("a", "b"), I("c")
    args = {"_": [(0, 2), (1, 3)]} if kind is T else {}
    p.e = kind(p.i, mutable=True, **args)
    values, mapping, selected = p.e._, p.e.map, p.e(p.a)
    args = {"_": [(2, 4)]} if kind is T else {}
    p.e = kind(p.j, **args)
    CHECK.assertEqual([member.n for member in values], [0, 1, 2])
    CHECK.assertEqual([member.n for member in mapping.values()], [0, 1, 2])
    CHECK.assertEqual(len(selected), 1)
    CHECK.assertIs(selected[0], values[0])


def test_parameter_selection_raw_write_is_local_and_preserves_capture():
    """Selection edits preserve the root and captured coefficients."""
    p = Prg()
    p.i = I("a", "b")
    p.x, p.k = V(p.i), P(p.i, _=[2, 3])
    selected = p.k(p.a)
    p.o = inf((selected * p.x(p.a))[0])
    selected._[0] = selected.map[(p.a,)] = 9
    np.testing.assert_array_equal(p.k._, [2, 3])
    np.testing.assert_array_equal(selected._, [9])
    np.testing.assert_array_equal(p.C, [2, 0])
