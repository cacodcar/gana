"""Bulk theta processing preserves exact arithmetic and fallback hooks."""

from collections import namedtuple
from fractions import Fraction
from importlib import import_module
from math import copysign, inf
from unittest import TestCase

import pytest

from gana import I, Prg, T
from gana.indexing.coordinates import encode_bounds
from gana.storage.parameters import NATIVE

CHECK = TestCase()
Bounds = namedtuple("Bounds", "lower upper")


@pytest.mark.parametrize(
    "pair",
    [
        (2**100, 2**100 + 1),
        (-(2**100 + 1), -(2**100)),
        (2**53 + 1, 2**53 + 2.0),
        (-inf, inf),
        (-0.0, 0.0),
    ],
)
def test_registered_batch_preserves_exact_endpoints_and_detaches(pair):
    """Adjacent large integers and zero signs survive bulk registration."""
    p = Prg()
    p.i = I(size=3)
    root = T(p.i, _=[(0, 1), pair, (3, 5)])
    staging = root._
    p.t = root
    staging[1] = (8, 9)
    CHECK.assertEqual((p.t[1].lb, p.t[1].ub), pair)
    CHECK.assertIs(type(p.t[1].lb), type(pair[0]))
    CHECK.assertIs(type(p.t[1].ub), type(pair[1]))
    CHECK.assertEqual(copysign(1, p.t[1].lb), copysign(1, pair[0]))
    CHECK.assertEqual(p.t[2].n, 2)


@pytest.mark.parametrize(
    ("pair", "error"),
    [
        ((2**100 + 1, 2**100), ValueError),
        ((2**53 + 1, float(2**53)), ValueError),
        ((float("nan"), 2**4096), ValueError),
        ((-(2**4096), float("nan")), OverflowError),
        ((0, 2**4096), OverflowError),
    ],
)
def test_late_invalid_pair_keeps_error_order_and_registration_atomic(
    pair,
    error,
):
    """Do not round before ordering or commit rows before a later failure."""
    p = Prg()
    p.i = I(size=3)
    root = T(p.i, _=(0, 1), name="declaration")
    root._[-1] = pair
    with pytest.raises(error):
        p.t = root
    CHECK.assertEqual(root.name, "declaration")
    CHECK.assertFalse(root.birthed)
    CHECK.assertEqual(p.n_thetas, 0)
    CHECK.assertNotIn("_symbol_storage", root.__dict__)
    root._[-1] = (2**100, 2**100 + 1)
    p.t = root
    CHECK.assertEqual(p.t[2].ub, 2**100 + 1)


class ObservedTheta(T):
    """An inherited validator can observe even ordinary built-in tuples."""

    calls = 0

    @staticmethod
    def _bound_pair(pair):
        """Count each accepted interval before applying the original rules."""
        ObservedTheta.calls += 1
        return T._bound_pair(pair)


def test_theta_subclass_keeps_its_validator():
    """The native shortcut must not bypass an inherited validation override."""
    ObservedTheta.calls = 0
    p = Prg()
    p.i = I(size=2)
    p.t = ObservedTheta(p.i, _=(0, 1))
    CHECK.assertEqual(ObservedTheta.calls, 4)
    CHECK.assertEqual((p.t[1].lb, p.t[1].ub), (0, 1))


@pytest.mark.skipif(not NATIVE, reason="native batch entry points")
def test_batch_callbacks_keep_nonprimitive_rows_in_order():
    """Boolean, Fraction, namedtuple and member rows retain Python handling."""
    native = import_module("gana._native")
    p = Prg()
    p.t = T(_=(1, 3))
    rows = [
        (0, 1),
        Bounds(2, 3),
        (False, True),
        (Fraction(-3, 2), Fraction(7, 4)),
        p.t[0],
    ]
    seen = []

    def validate(pair):
        """Record fallback row identities without modifying their values."""
        seen.append(pair)
        return T._bound_pair(pair)

    accepted = native.validate_bounds(rows, validate)
    CHECK.assertEqual(seen, rows[1:])
    CHECK.assertIsNot(accepted, rows)
    CHECK.assertEqual(
        accepted,
        [
            (0, 1),
            (2, 3),
            (False, True),
            (Fraction(-3, 2), Fraction(7, 4)),
            (1, 3),
        ],
    )
    seen.clear()

    def encode(pair):
        """Retain numeric-subclass conversion through the existing encoder."""
        seen.append(pair)
        return encode_bounds(pair)

    encoded = native.encode_bounds(accepted, encode)
    CHECK.assertEqual(encoded, [encode_bounds(pair) for pair in accepted])
    CHECK.assertEqual(seen, accepted[1:4])


class RefusingFloat(float):
    """Expose conversion hooks that a batch must neither skip nor repeat."""

    def __float__(self):
        """Fail before subsequent rows or a partially encoded batch escape."""
        message = "endpoint conversion refused"
        raise ValueError(message)


@pytest.mark.skipif(not NATIVE, reason="native batch entry points")
def test_batch_encoding_stops_at_subclass_failure():
    """An exception from an endpoint cannot be hidden by fast conversion."""
    native = import_module("gana._native")
    seen = []
    bad = (RefusingFloat(1), 2)
    later = Bounds(3, 4)

    def encode(pair):
        """Record the exact conversion order, including the failing row."""
        seen.append(pair)
        return encode_bounds(pair)

    with pytest.raises(ValueError, match="endpoint conversion refused"):
        native.encode_bounds([(0, 1), bad, later], encode)
    CHECK.assertEqual(seen, [bad])
