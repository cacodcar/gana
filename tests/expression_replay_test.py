"""Public row identity and mutable metadata during compatibility replay."""

from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V

CHECK = TestCase()


@pytest.mark.parametrize("theta", [False, True])
def test_replayed_siblings_own_mutable_metadata(theta):
    """Editing one public scalar must not change sibling or operand rows."""
    p = Prg()
    p.i = I(size=3)
    p.x = V(p.i)
    p.k = P(p.i, _=[2, 3, 5])
    source = p.k * p.x
    expression = source + (T(p.i, _=(-1, 4)) if theta else 7)
    selected = expression(p.i[::-1])
    row, sibling = expression[0], expression[1]
    CHECK.assertIs(selected[2], row)
    CHECK.assertIs(row.parent, expression)
    CHECK.assertEqual([child.A for child in expression], [[2], [3], [5]])
    CHECK.assertEqual(
        [child.B for child in expression],
        [0 if theta else -7] * 3,
    )

    # All empty compatibility containers remain independently mutable, even
    # when their initial contents and construction metadata are identical.
    for name in ("Y", "Z", "F", "_one", "_two"):
        getattr(row, name).append("edited")
        CHECK.assertEqual(getattr(sibling, name), [])
        CHECK.assertEqual(getattr(source[0], name), [])
    for name in ("X", "args", "_matrix", "map"):
        getattr(row, name)["edited"] = 19
        CHECK.assertNotIn("edited", getattr(sibling, name))
        CHECK.assertNotIn("edited", getattr(source[0], name))
    row.A[0] = 23
    CHECK.assertEqual(selected[2].A, [23])
    CHECK.assertEqual(sibling.A, [3])
    CHECK.assertEqual(source[0].A, [2])
    CHECK.assertIs(row.variables[0], p.x[0])
