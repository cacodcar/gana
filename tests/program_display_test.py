"""Frozen model-display outputs and independent tabular-value contracts."""

import json
from contextlib import ExitStack
from importlib import import_module
from itertools import product
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import pytest
from pandas import DataFrame
from pandas.testing import assert_frame_equal

from gana import I, Prg, V, inf, sigma
from gana.sets.constraint import C

CHECK = TestCase()
CATEGORIES = (None, "Capacity", "Costs", "missing", "")
DISPLAY_OPTIONS = [
    {
        "descriptive": descriptive,
        "categorical": categorical,
        "category": category,
    }
    for descriptive, categorical, category in product(
        (False, True),
        (False, True),
        CATEGORIES,
    )
]


def display_model(kind):
    """Build mixed row types and categories without invoking a solver."""
    program = Prg(name="Display contracts")
    if kind == "empty":
        return program
    program.i = I("a", "b")
    program.x = V(program.i)
    program.y = V(program.i, nn=False)
    capacity_limit, balance_total = 3, 5
    program.capacity = program.x <= capacity_limit
    program.capacity.category = "Capacity"
    program.balance = program.x + program.y == balance_total
    program.balance.category = "Balance"
    program.nonnegative = C(-program.x, leq=True, nn=True, category="Bounds")
    program.cost = 2 * program.x + program.y
    program.cost.category = "Costs"
    program.minimum = inf(sigma(program.cost))
    return program


def case_key(kind, options):
    """Identify an output fixture by its explicit public rendering options."""
    return json.dumps([kind, options], sort_keys=True)


def capture_show(program, options):
    """Capture ordered notebook events and public category-cache contents."""
    events = []

    def record(value):
        """Retain the display type as well as exact whitespace and content."""
        events.append([type(value).__name__, value.data])

    with ExitStack() as stack:
        for module in (
            "gana.block.program",
            "gana.sets.index",
            "gana.sets.objective",
            "gana.sets.constraint",
            "gana.sets.function",
        ):
            stack.enter_context(
                patch.object(import_module(module), "display", record),
            )
        result = program.show(**options)
    CHECK.assertIsNone(result)
    caches = {
        name: {
            category: [item.name for item in items]
            for category, items in getattr(program, name).items()
        }
        for name in ("categories", "fcategories")
        if hasattr(program, name)
    }
    return {"events": events, "caches": caches}


def frame_record(frame):
    """Record values, labels and column types for exact baseline comparison."""
    return {
        "frame": frame.to_dict(orient="split"),
        "dtypes": [str(dtype) for dtype in frame.dtypes],
    }


@pytest.fixture(scope="module")
def recorded_outputs():
    """Load immutable outputs recorded before the approved refactor."""
    path = Path(__file__).parent / "fixtures" / "program-display.json"
    return json.loads(path.read_text())["outputs"]


@pytest.mark.parametrize("kind", ["empty", "full"])
@pytest.mark.parametrize("options", DISPLAY_OPTIONS)
@pytest.mark.parametrize("as_document", [False, True])
def test_program_latex_matches_recorded_output(
    recorded_outputs,
    kind,
    options,
    as_document,
):
    """Preserve headings, category fallback, spacing and document wrapping."""
    arguments = {**options, "as_document": as_document}
    expected = recorded_outputs["latex"][case_key(kind, arguments)]
    CHECK.assertEqual(display_model(kind).latex(**arguments), expected)


@pytest.mark.parametrize("kind", ["empty", "full"])
@pytest.mark.parametrize("options", DISPLAY_OPTIONS)
@pytest.mark.parametrize("nncons", [False, True])
def test_program_show_matches_recorded_events(
    recorded_outputs,
    kind,
    options,
    nncons,
):
    """Preserve notebook events, optional bound rows and cached categories."""
    arguments = {**options, "nncons": nncons}
    expected = recorded_outputs["show"][case_key(kind, arguments)]
    CHECK.assertEqual(capture_show(display_model(kind), arguments), expected)


@pytest.mark.parametrize("longname", [False, True])
def test_dataframe_values_and_labels(recorded_outputs, longname):
    """Check known coefficients independently and retain label ordering."""
    program = display_model("full")
    label = "longname" if longname else "name"
    expected = DataFrame(
        [
            [2, 2, 1, 1, 0],
            [1, 0, 0, 0, 3],
            [0, 1, 0, 0, 3],
            [1, 0, 1, 0, 5],
            [0, 1, 0, 1, 5],
            [-1, 0, 0, 0, 0],
            [0, -1, 0, 0, 0],
        ],
        index=["Minimize"] + [getattr(row, label) for row in program.cons()],
        columns=[getattr(var, label) for var in program.variables] + ["RHS"],
        dtype=float,
    )
    matrix_before = program.A
    first = program.make_df(longname=longname)
    CHECK.assertEqual(
        frame_record(first),
        recorded_outputs["frames"][case_key("full", {"longname": longname})],
    )
    assert_frame_equal(first, expected, check_dtype=False)
    assert_frame_equal(program.make_df(longname=longname), first)
    CHECK.assertEqual(program.A, matrix_before)


@pytest.mark.parametrize("longname", [False, True])
def test_empty_dataframe(longname):
    """An empty model retains its objective placeholder and RHS column."""
    expected = DataFrame([[0]], index=["Minimize"], columns=["RHS"])
    assert_frame_equal(display_model("empty").make_df(longname), expected)


def test_plain_show_preserves_previous_category_caches():
    """Ordinary display must not clear the caches from a categorical view."""
    program = display_model("full")
    before = capture_show(program, {"categorical": True})["caches"]
    after = capture_show(program, {})["caches"]
    CHECK.assertEqual(after, before)
