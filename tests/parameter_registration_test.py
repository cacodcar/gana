"""Registration preserves staging validation and single-owner bookkeeping."""

from math import copysign, isnan
from unittest import TestCase

import pytest

from gana import I, P, Prg
from gana.storage.parameters import NATIVE

CHECK = TestCase()


class UnconvertibleFloat(float):
    """A raw numeric edit that must fail before program registration."""

    def __float__(self):
        """Expose conversion validation even when no mutation map is needed."""
        message = "cannot convert staged value"
        raise ValueError(message)


@pytest.mark.parametrize(
    ("value", "error"),
    [
        ("3", TypeError),
        (2**4096, OverflowError),
        (UnconvertibleFloat(3), ValueError),
    ],
)
def test_invalid_raw_values_fail_before_ownership(value, error):
    """Even aligned raw buffers must pass numeric conversion validation."""
    p = Prg()
    p.i = I(size=2)
    root = P(p.i, _=[1, 2], name="declaration")
    key = list(root.map)[-1]
    root._[-1] = value
    root.map[key] = value
    names = list(p.names)
    with pytest.raises(error):
        p.data = root
    CHECK.assertEqual(p.names, names)
    CHECK.assertEqual(p.n_parameter_sets, 0)
    CHECK.assertEqual(root.name, "declaration")
    CHECK.assertFalse(hasattr(p, "data"))
    CHECK.assertNotIn("_native_storage", root.__dict__)
    # A failed registration must not prevent a corrected retry.
    root._[-1] = 4.0
    root.map[key] = root._[-1]
    p.data = root
    CHECK.assertIs(p.data, root)
    CHECK.assertEqual(list(root._), [1, 4])


@pytest.mark.parametrize("edit", ["short", "mismatch", "reorder", "nan"])
def test_misaligned_staging_rejected(edit):
    """Registration checks lengths, ordered alignment and distinct NaNs."""
    p = Prg()
    p.i = I(size=2)
    root = P(p.i, _=[1, 2])
    key = next(iter(root.map))
    if edit == "short":
        root._.pop()
    elif edit == "mismatch":
        root.map[key] = 5
    elif edit == "reorder":
        root.map[key] = root.map.pop(key)
    else:
        root._[0] = float("nan")
        root.map[key] = float("nan")
    with pytest.raises(ValueError):
        p.data = root
    CHECK.assertEqual(p.parameter_sets, [])
    CHECK.assertFalse(hasattr(p, "data"))


@pytest.mark.parametrize("values", [2, [3, -2, 7], [float("nan"), -0.0, 5]])
def test_registration_consumes_values_and_preserves_ownership(values):
    """Scalar and nonuniform declarations retain their ordered coordinates."""
    p = Prg()
    p.i = I(size=3)
    root = P(p.i, _=values)
    old_values, old_map = root._, root.map
    keys = list(old_map)
    expected = list(old_values)
    p.data = root
    CHECK.assertIs(p.data, root)
    CHECK.assertIs(p.parameter_sets[0], root)
    CHECK.assertEqual(p.names_parameter_sets, ["data"])
    CHECK.assertEqual((p.n_parameter_sets, root.n), (1, 0))
    CHECK.assertIs(root._owner_root._program_token, p._owner_token)
    CHECK.assertEqual(list(root.map), keys)
    for actual, original in zip(root._, expected):
        if isnan(original):
            CHECK.assertTrue(isnan(actual))
        else:
            CHECK.assertEqual(actual, original)
            CHECK.assertEqual(copysign(1, actual), copysign(1, original))
    if NATIVE:
        old_values[-1] = 99
        old_map[keys[-1]] = 98
        CHECK.assertEqual(root._[-1], expected[-1])


def test_selected_parameter_cannot_acquire_a_second_program_owner():
    """Registration still rejects a selection bound to another program."""
    p = Prg()
    p.i = I("a", "b", "c")
    p.data = P(p.i, _=[1, 2, 3])
    selected = p.data(p.i[::-1])
    q = Prg()
    with pytest.raises(ValueError, match="another program"):
        q.data = selected
    CHECK.assertEqual(q.parameter_sets, [])
    CHECK.assertEqual(list(selected._), [3, 2, 1])
