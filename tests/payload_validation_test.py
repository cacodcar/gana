"""Constructor shortcuts preserve edited payloads and numeric edge cases."""

from collections import namedtuple
from fractions import Fraction
from math import copysign, inf, isnan
from unittest import TestCase

import pytest

from gana import I, P, Prg, T
from gana.storage.parameters import NATIVE

CHECK = TestCase()
Bounds = namedtuple("Bounds", "lower upper")


class UnconvertibleFloat(float):
    """An equal numeric edit whose conversion must still run and fail."""

    def __float__(self):
        """Reject conversion to expose accidental subclass acceptance."""
        message = "cannot convert edited payload"
        raise ValueError(message)


@pytest.mark.skipif(not NATIVE, reason="compact native declaration buffers")
@pytest.mark.parametrize("value", [0.0, -0.0, inf, -inf, float("nan")])
def test_compact_float_values_preserve_special_values_and_detach(value):
    """Keep IEEE values without retaining editable raw buffers."""
    p = Prg()
    p.i = I(size=2)
    root = P(p.i, _=[value, 3])
    staged_values, staged_map = root._, root.map
    CHECK.assertTrue(staged_map.compact)
    p.data = root
    CHECK.assertTrue(staged_map.compact)
    actual = root._[0]
    if isnan(value):
        CHECK.assertTrue(isnan(actual))
    else:
        CHECK.assertEqual(actual, value)
        CHECK.assertEqual(copysign(1, actual), copysign(1, value))
    staged_values[-1] = 99
    CHECK.assertEqual(root._[-1], 3)


@pytest.mark.skipif(not NATIVE, reason="compact native declaration buffers")
@pytest.mark.parametrize(
    ("edit", "error"),
    [("3", TypeError), (4.0, ValueError), (UnconvertibleFloat(3), ValueError)],
)
def test_compact_edits_fail_atomically_and_allow_corrected_retry(edit, error):
    """Equal subclasses and unequal raw edits cannot bypass validation."""
    p = Prg()
    p.i = I(size=2)
    root = P(p.i, _=[1, 3], name="declaration")
    root._[-1] = edit
    names = list(p.names)
    with pytest.raises(error):
        p.data = root
    CHECK.assertEqual(p.names, names)
    CHECK.assertEqual(p.n_parameter_sets, 0)
    CHECK.assertEqual(root.name, "declaration")
    CHECK.assertNotIn("_native_storage", root.__dict__)
    CHECK.assertTrue(root.map.compact)
    root._[-1] = float("3")
    p.data = root
    CHECK.assertEqual(list(root._), [1, 3])


@pytest.mark.parametrize(
    "pair",
    [Bounds(-2, 5), (Fraction(-3, 2), Fraction(7, 4)), (False, True)],
)
def test_theta_nonstandard_pairs_survive_registration(pair):
    """Preserve conversion of tuple subclasses and non-built-in endpoints."""
    p = Prg()
    p.i = I(size=2)
    p.t = T(p.i, _=[pair, (-0.0, inf)])
    CHECK.assertEqual((p.t[0].lb, p.t[0].ub), pair)
    CHECK.assertEqual(copysign(1, p.t[1].lb), -1)
    CHECK.assertEqual(p.t[1].ub, inf)


def test_theta_member_payload_is_read_again_after_declaration_edit():
    """Existing member payloads remain accepted and are validated afresh."""
    p = Prg()
    p.i = I(size=1)
    p.source = T(_=(1, 3))
    root = T(p.i, _=[p.source[0]])
    root._[0] = Bounds(-5, 9)
    p.target = root
    CHECK.assertEqual((p.target[0].lb, p.target[0].ub), (-5, 9))
    CHECK.assertEqual((p.source[0].lb, p.source[0].ub), (1, 3))


@pytest.mark.skipif(not NATIVE, reason="compact native declaration buffers")
@pytest.mark.parametrize(
    ("original", "edited"),
    [("2.5", "2.5"), ("0.0", "-0.0"), ("inf", "inf")],
)
def test_equal_float_edits_preserve_the_accepted_value(original, edited):
    """Accept equal detached floats and retain the edited zero's sign."""
    p = Prg()
    p.i = I(size=1)
    root = P(p.i, _=[float(original)])
    before = root._[0]
    value = float(edited)
    CHECK.assertIsNot(before, value)
    root._[0] = value
    staged = root.map
    p.data = root
    CHECK.assertTrue(staged.compact)
    CHECK.assertEqual(root._[0], value)
    CHECK.assertEqual(copysign(1, root._[0]), copysign(1, value))


@pytest.mark.skipif(not NATIVE, reason="compact native declaration buffers")
def test_distinct_nan_edit_is_rejected_without_expanding_the_map():
    """Identity acceptance of NaN must not turn unequal NaNs into a match."""
    p = Prg()
    p.i = I(size=1)
    root = P(p.i, _=[float("nan")], name="declaration")
    root._[0] = float("nan")
    with pytest.raises(ValueError, match="disagree"):
        p.data = root
    CHECK.assertTrue(root.map.compact)
    CHECK.assertEqual(root.name, "declaration")
    CHECK.assertEqual(p.n_parameter_sets, 0)
    CHECK.assertNotIn("_native_storage", root.__dict__)


class UnequalFloat(float):
    """Keep a mapped subclass's observable inequality authoritative."""

    comparisons = 0

    def __ne__(self, other):
        """Reject equality and count validation's calls to this hook."""
        self.comparisons += 1
        return True


@pytest.mark.skipif(not NATIVE, reason="compact native declaration buffers")
def test_mapped_float_subclass_keeps_its_inequality_hook():
    """A primitive value must not bypass the mapped object's comparison."""
    p = Prg()
    p.i = I(size=1)
    root = P(p.i, _=[2])
    mapped = UnequalFloat(2)
    root.map.fill([mapped])
    with pytest.raises(ValueError, match="disagree"):
        p.data = root
    CHECK.assertEqual(mapped.comparisons, 1)
    CHECK.assertTrue(root.map.compact)
    CHECK.assertEqual(p.n_parameter_sets, 0)
