"""Behavioral contracts for the release-quality complexity refactor."""

from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase

import pytest
from matplotlib import pyplot as plt

from gana import I, Prg, V
from gana.block.solution import Solution
from gana.value.zero import Z

CHECK = TestCase()


@pytest.mark.parametrize(
    "left_negative,right_negative,expected",
    [
        (False, False, False),
        (False, True, False),
        (True, False, True),
        (True, True, False),
    ],
)
def test_signed_zero_order_is_preserved(
    left_negative,
    right_negative,
    expected,
):
    """Retain Gana's existing signed-zero ordering, including equal signs."""
    left, right = Z(neg=left_negative), Z(neg=right_negative)
    CHECK.assertIs(left > right, expected)
    CHECK.assertIs(left >= right, expected)
    CHECK.assertIs(left < right, not expected)
    CHECK.assertIs(left <= right, not expected)


@pytest.mark.parametrize("negative", [False, True])
@pytest.mark.parametrize(
    "number,expected",
    [
        (-float("inf"), True),
        (-3, True),
        (-0.0, False),
        (0, False),
        (2.5, False),
        (float("inf"), False),
        (float("nan"), None),
        (object(), None),
    ],
)
def test_zero_numeric_and_unordered_results(negative, number, expected):
    """NaN and unsupported operands retain the existing None result."""
    CHECK.assertIs(Z(neg=negative).__gt__(number), expected)


def solved_variable():
    """Build independent solution values with one absent solution entry."""
    program = Prg()
    program.i = I("a", "b", "c")
    program.x = V(program.i)
    program.x[0].X.update({0: 3.0, 1: 8.0})
    program.x[1].X.update({1: 9.0})
    program.x[2].X.update({0: -2.0})
    return program.x


@pytest.mark.parametrize(
    "options,expected",
    [
        ({"aslist": True}, [3.0, -2.0]),
        ({"aslist": True, "asdict": True}, [3.0, -2.0]),
        ({"n_sol": 1, "aslist": True}, [8.0, 9.0]),
        ({"n_sol": 10, "aslist": True}, []),
    ],
)
def test_output_list_precedence_and_missing_solutions(options, expected):
    """List output wins over dictionary output and omits missing entries."""
    CHECK.assertEqual(solved_variable().output(**options), expected)


def test_output_dictionary_keeps_coordinate_keys():
    """Dictionary output retains registered keys and their original order."""
    variable = solved_variable()
    keys = list(variable.map)
    CHECK.assertEqual(
        variable.output(asdict=True),
        {keys[0]: 3.0, keys[2]: -2.0},
    )


@pytest.mark.parametrize("compare", [False, True])
def test_output_display_precedence(monkeypatch, compare):
    """Compare overrides return modes; ordinary display omits missing data."""
    variable = solved_variable()
    displayed = []
    monkeypatch.setattr(
        import_module("gana.sets.variable"),
        "display",
        displayed.append,
    )
    options = (
        {"compare": True, "aslist": True, "asdict": True} if compare else {}
    )
    CHECK.assertIsNone(variable.output(**options))
    values = ["3.0, 8.0", "9.0", "-2.0"] if compare else ["3.0", "-2.0"]
    members = list(variable) if compare else [variable[0], variable[2]]
    CHECK.assertEqual(
        [item.data for item in displayed],
        [v.latex() + "=" + value for v, value in zip(members, values)],
    )


@pytest.mark.parametrize("kind", ["line", "bar", "unknown"])
@pytest.mark.parametrize("ticks_limit", [1, 20])
def test_solution_plot_preserves_data_and_coordinate_labels(
    monkeypatch,
    kind,
    ticks_limit,
):
    """Check plot geometry and fixed-coordinate labels without TeX."""
    data = {
        "values": [4.0, -2.0],
        "index": [{"site": {}, "morning": {}}, {"site": {}, "evening": {}}],
        "index_latex": ["$site,morning$", "$site,evening$"],
    }

    def selected_data(_solution, _variable):
        """Supply output independently of the plotting implementation."""
        return data

    monkeypatch.setattr(Solution, "__call__", selected_data)
    try:
        Solution().draw(
            SimpleNamespace(tag="x", name="fallback"),
            kind=kind,
            usetex=False,
            x_ticks_lim=ticks_limit,
        )
        axes = plt.gca()
        CHECK.assertEqual(axes.get_title(), "$x$ (site)")
        CHECK.assertEqual(axes.get_xlabel(), "Indices")
        CHECK.assertEqual(axes.get_ylabel(), "Values")
        if kind == "line":
            CHECK.assertEqual(list(axes.lines[0].get_ydata()), [4.0, -2.0])
        elif kind == "bar":
            CHECK.assertEqual(
                [bar.get_height() for bar in axes.patches],
                [4.0, -2.0],
            )
        else:
            CHECK.assertEqual(len(axes.lines) + len(axes.patches), 0)
        if ticks_limit >= len(data["values"]):
            CHECK.assertEqual(
                [label.get_text() for label in axes.get_xticklabels()],
                ["$morning$", "$evening$"],
            )
    finally:
        plt.close("all")
