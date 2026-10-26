"""Placeholder detection must not perform algebra on symbolic coordinates."""

from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, Prg, V, sigma
from gana.indexing.selection import Selection, has_placeholders

CHECK = TestCase()


class Coordinate:
    """Hashable identity whose equality forbids a placeholder comparison."""

    __hash__ = object.__hash__

    def __eq__(self, other):
        """Allow membership comparisons but reject placeholder equality."""
        if other is None:
            message = "Placeholder detection invoked equality"
            raise AssertionError(message)
        return self is other


@pytest.mark.parametrize("mode", ["regular", "repeat", "gap", "empty"])
def test_placeholder_detection_uses_identity(mode):
    """Detect real skips/repeats without comparing a coordinate to None."""
    a, b = Coordinate(), Coordinate()
    axes = {
        "regular": ((a, b),),
        "repeat": ((a, a),),
        "gap": ((a, None),),
        "empty": ((), (a,)),
    }
    CHECK.assertEqual(has_placeholders(axes[mode]), mode in {"repeat", "gap"})


@pytest.mark.parametrize("kind", ["p", "v", "t"])
@pytest.mark.parametrize("mode", ["regular", "repeat", "gap", "empty"])
def test_selection_gap_policy_and_copy(kind, mode):
    """Preserve each kind's list/map policy and copied coordinate aliases."""
    a, b = Coordinate(), Coordinate()
    axes = {
        "regular": ((a, b),),
        "repeat": ((a, a),),
        "gap": ((a, None),),
        "empty": ((), (a,)),
    }
    selection = Selection({(a,): 3, (b,): 7}, axes[mode], kind)
    CHECK.assertEqual(selection.skipped, mode == "gap")
    sizes = {
        "regular": 2,
        "repeat": 1,
        "gap": 1 if kind == "t" else 2,
        "empty": 0,
    }
    CHECK.assertEqual(selection.map_size(), sizes[mode])
    CHECK.assertEqual(len(list(selection.keys())), sizes[mode])
    clone, copied_axis = deepcopy((selection, a))
    CHECK.assertEqual(clone.skipped, selection.skipped)
    CHECK.assertEqual(clone.map_size(), selection.map_size())
    if mode != "empty":
        CHECK.assertIs(clone.axes[0][0], copied_axis)
        CHECK.assertEqual(clone.value((copied_axis,)), 3)


@pytest.mark.parametrize("kind", ["p", "v", "t"])
def test_symbolic_coordinate_does_not_construct_a_constraint(
    kind,
    monkeypatch,
):
    """V coordinates must not construct constraints during skip checks."""
    p = Prg()
    p.i = I(size=3)
    p.x = V(p.i)
    constraint_count = p.n_constraints
    equality = V.__eq__

    def compare(variable, other):
        """Reject placeholder comparisons; preserve symbolic equality."""
        if other is None:
            message = "Built a constraint to detect a placeholder"
            raise AssertionError(message)
        return equality(variable, other)

    monkeypatch.setattr(V, "__eq__", compare)
    axes = ((p.x,),)
    CHECK.assertFalse(has_placeholders(axes))
    selected = Selection({(p.x,): 9}, axes, kind)
    CHECK.assertFalse(selected.skipped)
    CHECK.assertEqual(selected.mapped_value((p.x,)), 9)
    CHECK.assertEqual(p.n_constraints, constraint_count)


def test_axis_reduction_of_nested_view_preserves_numeric_rows():
    """Selection and sigma preserve expected columns and coefficients."""
    p = Prg()
    p.i, p.j = I(size=4), I(size=2)
    p.x = V(p.i, p.j)
    view = p.x(p.i[::-1], p.j)
    reduced = sigma(view, view.index[0])
    rows = [dict(zip(row.P, row.A)) for row in reduced]
    CHECK.assertEqual(
        rows,
        [{0: 1, 2: 1, 4: 1, 6: 1}, {1: 1, 3: 1, 5: 1, 7: 1}],
    )
