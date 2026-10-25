"""
Direct formula rendering preserves legacy text without exposing Python rows.
"""

from copy import deepcopy
from unittest import TestCase

import pytest
from IPython.core.formatters import DisplayFormatter
from IPython.lib.pretty import pretty

from gana import I, P, Prg, T, V, inf, sigma, sup
from gana.backends.native.algebra import NativeRows
from gana.sets.function import F

CHECK = TestCase()


def model(size=12):
    """Keep symbols untouched and coefficients distinct before each display."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i, mutable=True)
    p.y = V(p.i)
    p.k = P(p.i, _=list(range(1, size + 1)))
    p.t = T(p.i, _=(-2, 3))
    return p


def nodes(source):
    """
    Inspect native recipes by identity, without reading compatibility data.
    """
    result, pending = {}, [source]
    while pending:
        value = pending.pop()
        if isinstance(value, NativeRows) and id(value) not in result:
            result[id(value)] = value
            pending.extend(value._native_recipe[1:])
    return tuple(result.values())


def display(value):
    """
    Check all three text entry points and mathematical notebook rendering.
    """
    return str(value), repr(value), value.latex(), value.longname


BUILDERS = [
    lambda p: p.k * p.x + 3,
    lambda p: p.x - (p.y + p.k),
    lambda p: p.k - (p.x + p.y),
    lambda p: -(p.x + p.y),
    lambda p: 0.5 * (20 * p.x + p.y),
    lambda p: p.k * (p.x - 2 * p.y),
    lambda p: p.x + p.t,
    lambda p: p.t - p.x,
    lambda p: p.x + (-2 * p.t),
    lambda p: -3 * (p.x + p.t),
    lambda p: p.k * p.x + T(p.i, _=(-3, 4)),
    lambda p: (p.k * p.x + 3)(p.i[::-2]),
    lambda p: (p.x + p.y)(p.i[:0]),
    lambda p: sigma(p.k * p.x),
    lambda p: -sigma(p.k * p.x),
    lambda p: 2 * sigma(p.k * p.x),
    lambda p: inf(sigma(p.k * p.x)).function,
    lambda p: sup(sigma(p.k * p.x)).function,
    lambda p: inf(p.k(p.i[:1]) * p.x(p.i[:1])).function,
]


@pytest.mark.parametrize("build", BUILDERS)
def test_direct_display_matches_replay_without_exposing_rows(build):
    """Independent legacy replay is the formatting oracle for each recipe."""
    p = model()
    expression = build(p)
    CHECK.assertIsInstance(expression, NativeRows)
    reference = deepcopy(expression)._materialize()
    expected = display(reference)
    for _ in range(2):
        CHECK.assertEqual(display(expression), expected)
        for node in nodes(expression):
            CHECK.assertNotIn("_legacy_cache", node.__dict__)
    # Scalar objective display can inspect its one visible member, but never
    # the unused members of a vector owner.
    CHECK.assertLessEqual(len(p.x._symbol_storage.states), 1)
    CHECK.assertEqual(p.y._symbol_storage.states, {})
    CHECK.assertEqual(p.t._symbol_storage.states, {})


@pytest.mark.parametrize("size", [1, 2, 3, 1000])
@pytest.mark.parametrize("axis", [False, True])
@pytest.mark.parametrize(
    "operation",
    [lambda f: f, lambda f: -f, lambda f: 2 * f, lambda f: f + 4],
)
def test_variable_reduction_formats_without_bulk_members(
    size,
    axis,
    operation,
):
    """Retain short-sum syntax and compact larger V reductions exactly."""
    p = model(size)
    p.j = I(size=3)
    p.grid = V(p.i, p.j)
    expression = operation(sigma(p.grid, p.i) if axis else sigma(p.x))
    reference = deepcopy(expression)._materialize()
    CHECK.assertEqual(str(expression), str(reference))
    CHECK.assertEqual(expression.latex(), reference.latex())
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)
    CHECK.assertLessEqual(len(p.x._symbol_storage.states), 2)
    CHECK.assertEqual(p.grid._symbol_storage.states, {})


def test_display_does_not_replay_or_change_compilation(monkeypatch):
    """A large indexed expression stays native for later algebra and export."""
    p = model(1000)
    source = p.k * p.x + p.t
    selected = source(p.i[::-2])

    def reject_replay(self):
        """Fail if a text request exposes any compatibility expression rows."""
        pytest.fail("display reconstructed Python expression rows")

    monkeypatch.setattr(NativeRows, "_replay_rows", reject_replay)
    for expression in (source, selected, 2 * selected, sigma(selected)):
        display(expression)
        CHECK.assertTrue(expression._is_lazy())
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertEqual(p.t._symbol_storage.states, {})
    bound = 5
    p.c = selected <= bound
    CHECK.assertEqual(p.A_sparse.shape, (500, 2000))


def test_exposed_metadata_and_row_edits_remain_authoritative():
    """Display must honor live edits and preserve selected-row identity."""
    p = model()
    source = p.k * p.x
    selected = source(p.i[:2])
    display(selected)
    source[0].one = 99
    source[0].give_name()
    source._legacy_cache.name = "edited root"
    source._legacy_cache.two._ltx = "custom"
    CHECK.assertEqual(str(source), "edited root")
    CHECK.assertEqual(source.latex(), source._legacy_cache.latex())
    CHECK.assertIs(selected[0], source[0])
    CHECK.assertIn("99", str(selected[0]))


def test_printing_preserves_captured_coefficients_and_registration():
    """Read-only display does not expose dependent rows or freeze labels."""
    p = model()
    source = p.k * p.x
    selected = source(p.i[:1])
    objective = inf(selected)
    expected = objective.latex()
    p.k._[:] = [99] * 12
    CHECK.assertEqual(objective.latex(), expected)
    CHECK.assertEqual(objective.matrix, {0: 1})
    p.total = sigma(source)
    p.total.category = "Costs"
    p.o = inf(p.total)
    CHECK.assertEqual(p.o.function.category, "Costs")
    p.total.category = "Updated"
    CHECK.assertEqual(p.o.function.category, "Updated")
    for expression in (source, selected, p.total, p.o.function):
        CHECK.assertNotIn("_legacy_cache", expression.__dict__)


def test_failed_render_restores_normal_construction(monkeypatch):
    """Formatting errors must never leave the metadata-only factory active."""
    p = model()
    expression = p.k * p.x

    def fail_format(self):
        """Exercise context cleanup at a formatter failure boundary."""
        message = "format failure"
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(F, "give_name", fail_format)
        with pytest.raises(RuntimeError, match="format failure"):
            str(expression)
    following = p.k * p.x + 3
    CHECK.assertIsInstance(following, NativeRows)
    CHECK.assertEqual(following[0].A, [1])


@pytest.mark.parametrize("axis", [False, True])
def test_variable_sum_objective_retains_scalar_label(axis):
    """A one-output V sum retains O's special scalar formatting selection."""
    p = model(3)
    p.j = I(size=1)
    p.grid = V(p.i, p.j)
    source = sigma(p.grid, p.i) if axis else sigma(p.x)
    expression = inf(source).function
    reference = deepcopy(expression)._materialize()
    CHECK.assertEqual(str(expression), str(reference))
    CHECK.assertEqual(expression.latex(), reference.latex())
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)


def test_scalar_objective_display_retains_nonzero_registered_row_id():
    """Project registered scalar IDs independently of the collection's ID."""
    p = model()
    p.first = p.x + 1
    p.term = p.k(p.i[:1]) * p.x(p.i[:1])
    p.o = inf(p.term)
    number = p.o.function.n
    CHECK.assertEqual(number, 12)
    CHECK.assertNotIn("_legacy_cache", p.term.__dict__)
    CHECK.assertEqual(number, p.o.function._materialize().n)


def test_scalar_objective_display_follows_later_shared_selection_numbers():
    """Rendering cannot give shared rows a different ID from public replay."""
    p = model(1)
    p.term = p.k * p.x
    p.o = inf(p.term)
    p.selected = p.term(p.i)
    number = p.o.function.n
    CHECK.assertEqual(number, 1)
    CHECK.assertNotIn("_legacy_cache", p.term.__dict__)
    CHECK.assertEqual(number, p.o.function._materialize().n)


def test_notebook_display_protocol_probes_do_not_materialize():
    """IPython's optional rich-format probes must reach the lazy plain repr."""
    p = model(1000)
    expression = p.k * p.x + p.t
    expected = str(expression)
    CHECK.assertEqual(pretty(expression), expected)
    data, metadata = DisplayFormatter().format(expression)
    CHECK.assertEqual(data, {"text/plain": expected})
    CHECK.assertEqual(metadata, {})
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertEqual(p.t._symbol_storage.states, {})
    for node in nodes(expression):
        CHECK.assertNotIn("_legacy_cache", node.__dict__)
