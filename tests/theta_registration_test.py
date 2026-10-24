"""Registration safety and exact endpoints for constructor fast paths."""

from copy import deepcopy
from fractions import Fraction
from math import copysign, inf
from unittest import TestCase

import numpy as np
import pytest

from gana import I, Prg, T
from gana.indexing.coordinates import decode_bounds, encode_bounds
from gana.storage.parameters import NATIVE

CHECK = TestCase()


@pytest.mark.parametrize("register", [False, True])
@pytest.mark.parametrize(
    ("invalid", "error"),
    [
        ((4, 2), ValueError),
        ((0, float("nan")), ValueError),
        ((float("nan"), 2), ValueError),
        ((0, "3"), TypeError),
        ((1,), ValueError),
        ([0, 1], ValueError),
    ],
)
def test_post_construction_invalid_bounds_fail_before_registration(
    register,
    invalid,
    error,
):
    """Neither direct birth nor registration may trust earlier validation."""
    p = Prg()
    p.i = I(size=2)
    p.old = T(_=(1, 2))
    root = T(p.i, _=[(0, 3), (0, 3)], name="declaration")
    root._[-1] = invalid
    names, sets = list(p.names), list(p.names_theta_sets)
    with pytest.raises(error):
        if register:
            p.t = root
        else:
            root.birth_thetas(n_start=1)
    CHECK.assertEqual(p.names, names)
    CHECK.assertEqual(p.names_theta_sets, sets)
    CHECK.assertEqual((p.n_theta_sets, p.n_thetas), (1, 1))
    CHECK.assertFalse(hasattr(p, "t"))
    CHECK.assertEqual(root.name, "declaration")
    CHECK.assertFalse(root.birthed)
    CHECK.assertNotIn("_symbol_storage", root.__dict__)


@pytest.mark.parametrize("register", [False, True])
def test_post_construction_length_changes_fail_without_birth(register):
    """A truncated staging list cannot silently shorten a registered domain."""
    p = Prg()
    p.i = I(size=2)
    root = T(p.i, _=(0, 3))
    root._.pop()
    with pytest.raises(ValueError, match="length must match"):
        if register:
            p.t = root
        else:
            root.birth_thetas()
    CHECK.assertEqual(p.n_thetas, 0)
    CHECK.assertFalse(root.birthed)


@pytest.mark.parametrize("register", [False, True])
def test_valid_edits_are_consumed_with_exact_bounds_and_stable_members(
    register,
):
    """Fresh bounds and column identity survive birth and deep copying."""
    p = Prg()
    p.i = I(size=2)
    p.old = T(_=(1, 2))
    large = 2**100 + 1
    root = T(p.i, _=[(0, 3), (0, 3)])
    root._[:] = [(-large, large), (-inf, -0.0)]
    if register:
        p.t = root
    else:
        root.birth_thetas(n_start=1)
    if NATIVE:
        CHECK.assertEqual(root._symbol_storage.states, {})
    first = root[0]
    CHECK.assertEqual((first.lb, first.ub, first.n), (-large, large, 1))
    CHECK.assertIs(first.parent, root)
    CHECK.assertEqual((root[1].lb, root[1].ub, root[1].n), (-inf, -0.0, 2))
    CHECK.assertEqual(copysign(1, root[1].ub), -1)
    root.birth_thetas(n_start=50)
    CHECK.assertIs(root[0], first)
    CHECK.assertEqual(first.n, 1)
    restored = deepcopy(root)
    CHECK.assertEqual((restored[0].lb, restored[0].ub), (-large, large))
    CHECK.assertEqual(copysign(1, restored[1].ub), -1)


class DecoratedInt(int):
    """An int subclass whose display must not become the encoded integer."""

    def __str__(self):
        """Expose accidental subclass formatting in an integer fast path."""
        return "decorated"


@pytest.mark.parametrize(
    ("pair", "expected"),
    [
        ((-(2**4096), 2**4096 + 1), (-(2**4096), 2**4096 + 1)),
        ((False, True), (0, 1)),
        ((DecoratedInt(-7), DecoratedInt(11)), (-7, 11)),
        ((np.int64(-5), np.uint64(2**64 - 1)), (-5, 2**64 - 1)),
        ((-inf, inf), (-inf, inf)),
        ((-0.0, 0.0), (-0.0, 0.0)),
        ((np.float32(-1.25), np.float64(2.5)), (-1.25, 2.5)),
        ((Fraction(-3, 2), Fraction(7, 4)), (-1.5, 1.75)),
        ((-(2**100 + 1), 0.5), (-(2**100 + 1), 0.5)),
    ],
)
def test_endpoint_encoding_roundtrips_exact_integers_and_numeric_fallbacks(
    pair,
    expected,
):
    """Built-in fast paths retain the previous numeric-subclass conversion."""
    actual = decode_bounds(encode_bounds(pair))
    CHECK.assertEqual(actual, expected)
    CHECK.assertEqual(
        tuple(type(value) for value in actual),
        tuple(type(value) for value in expected),
    )
    CHECK.assertEqual(
        tuple(
            copysign(1, value) for value in actual if isinstance(value, float)
        ),
        tuple(
            copysign(1, value)
            for value in expected
            if isinstance(value, float)
        ),
    )


def test_unbounded_coordinate_marker_is_preserved():
    """Coordinates without theta bounds keep the native None marker."""
    CHECK.assertIsNone(encode_bounds(None))
