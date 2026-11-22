"""Plot extraction preserves coordinates, solution identity and model state."""

import numpy as np
import pytest
from matplotlib import pyplot as plt

from gana import I, P, Prg, V, inf, plotting, sigma


@pytest.fixture(autouse=True)
def close_figures():
    """Keep plotting tests independent of the interactive figure registry."""
    yield
    plt.close("all")


def model():
    p = Prg()
    p.t = I(size=3)
    p.a = P(p.t, _=[1, 0, -2])
    p.b = P(p.t, _=[3, 4, -1])
    return p


def test_element_program_and_addition_have_identical_grouped_geometry():
    p = model()
    left = p.a.bar()
    before = plt.get_fignums()
    combined = left + p.bar(p.b)
    assert plt.get_fignums() == before
    one = combined.render()
    two = p.bar(p.a, p.b).render()
    first = [
        (b.get_x(), b.get_width(), b.get_height()) for b in one.axes[0].patches
    ]
    second = [
        (b.get_x(), b.get_width(), b.get_height()) for b in two.axes[0].patches
    ]
    assert first == second
    assert len(left.data) == 1
    assert [s.values for s in combined.data] == [(1, 0, -2), (3, 4, -1)]


def test_right_to_left_dimensions_and_stable_panel_encoding():
    p = model()
    p.site = I("north", "south")
    p.scenario = I("low", "high")
    p.profile = P(p.site, p.scenario, p.t, _=list(range(12)))
    plot = p.profile.line()
    assert [s.values for s in plot.data] == [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (9, 10, 11),
    ]
    assert [s.x for s in plot.data] == [(0, 1, 2)] * 4
    result = plot.render()
    assert len(result.axes) == 2
    assert (
        result.axes[0].lines[0].get_color()
        == result.axes[1].lines[0].get_color()
    )
    selected = p.profile(p.south, p.scenario, p.t).line()
    assert [s.values for s in selected.data] == [(6, 7, 8), (9, 10, 11)]
    transposed = p.profile.line(x=p.scenario, series=p.t, panel=p.site)
    assert transposed.data[0].values == (0, 3)
    assert transposed.data[0].x == ("low", "high")


def test_extra_dimensions_require_selection_and_roles_cannot_overlap():
    p = model()
    p.a1 = I("one", "two")
    p.a2 = I("red", "blue")
    p.a3 = I("east", "west")
    p.q = P(p.a1, p.a2, p.a3, p.t, _=list(range(24)))
    with pytest.raises(ValueError, match="remaining index dimensions"):
        p.q.line()
    assert len(p.q(p.one, p.a2, p.a3, p.t).line().data) == 4
    with pytest.raises(ValueError, match="distinct plotting role"):
        p.q.line(x=0, series=0)
    with pytest.raises(ValueError, match="Axis selectors"):
        p.a.line(x="unknown")


def test_coordinate_identity_checks_can_be_disabled(monkeypatch):
    p = model()
    p.other = I(size=3)
    p.c = P(p.other, _=[10, 20, 30])
    plot = p.a.line() + p.c.line()
    assert plotting.CHECK_INDICES is True
    with pytest.raises(ValueError, match="index domains"):
        plot.render()
    monkeypatch.setattr(plotting, "CHECK_INDICES", False)
    result = plot.render()
    assert len(result.axes[0].lines) == 2


def test_stacking_checks_order_while_lines_allow_different_sampling():
    p = model()
    subset = p.t[1:]
    plot = p.a.line() + p.b(subset).line()
    result = plot.render()
    np.testing.assert_equal(result.axes[0].lines[1].get_xdata(), [1, 2])
    with pytest.raises(ValueError, match="matching coordinate order"):
        p.stacked(p.a, p.b(subset)).render()


def test_panel_composition_rejects_different_locations():
    p = model()
    p.site = I("north", "south")
    p.scenario = I("low", "high")
    p.q = P(p.site, p.scenario, p.t, _=list(range(12)))
    with pytest.raises(ValueError, match="panel indices"):
        (p.q.line() + p.a.line()).render()


def test_explicit_solution_number_and_snapshot_do_not_mutate_native_state():
    p = model()
    p.v = V(p.t)
    p.c = p.v >= p.a
    p.cost = inf(sigma(p.v))
    p.opt()
    storage = p.v._symbol_storage.owner
    before = (len(storage.states), len(storage.cache), tuple(p.X[0]))
    first = p.v.line(n_sol=0)
    assert before == (len(storage.states), len(storage.cache), tuple(p.X[0]))
    assert first.data[0].values == (1, 0, 0)
    p.more = p.v >= p.b
    p.opt()
    assert p.line(p.v, n_sol=1).data[0].values == (3, 4, 0)
    assert first.data[0].values == (1, 0, 0)
    assert first.data[0].n_sol == 0
    scalar = p.v[0].line(n_sol=1)
    assert scalar.data[0].values == (3,)
    with pytest.raises(ValueError, match="No stored solution"):
        p.v.line(n_sol=7)


def test_unsolved_variables_raise_and_omitted_columns_stay_missing():
    p = model()
    p.v = V(p.t)
    with pytest.raises(ValueError, match="No stored solution"):
        p.v.bar()
    p.c = p.v[0] >= 0
    p.cost = inf(p.v[0])
    p.opt()
    assert p.v.line().data[0].values == (0, None, None)


def test_value_against_value_scatter_uses_indexed_x():
    p = model()
    plot = p.b.scatter(x=p.a)
    result = plot.render()
    np.testing.assert_equal(
        result.axes[0].collections[0].get_offsets(), [[1, 3], [0, 4], [-2, -1]]
    )
    p.other = I(size=3)
    p.c = P(p.other, _=[1, 2, 3])
    with pytest.raises(ValueError, match="matching indices"):
        p.b.scatter(x=p.c)


def test_bounds_keep_selected_coordinate_order():
    p = model()
    p.lower = P(p.t, _=[0, -1, -3])
    p.upper = P(p.t, _=[2, 1, -1])
    plot = p.band(p.a, lower=p.lower, upper=p.upper)
    assert plot.data[0].lower == (0, -1, -3)
    assert plot.data[0].upper == (2, 1, -1)
    with pytest.raises(ValueError, match="matching indices"):
        p.a.band(lower=p.lower(p.t[1:]), upper=p.upper)


def test_missing_values_are_copied_without_zero_filling():
    values = [0, None, 3]
    plot = plotting.line(values)
    values[0] = 99
    assert plot.data[0].values == (0, None, 3)
    result = plot.render()
    np.testing.assert_equal(
        result.axes[0].lines[0].get_ydata(), [0, np.nan, 3]
    )


def test_disabled_checks_leave_shape_errors_to_matplotlib(monkeypatch):
    monkeypatch.setattr(plotting, "CHECK_INDICES", False)
    plot = plotting.scatter([1, 2], x=[0, 1, 2])
    with pytest.raises(ValueError, match="same size"):
        plot.render()


def test_scatter_quantity_axis_cannot_silently_become_an_index_axis():
    p = model()
    with pytest.raises(ValueError, match="index domains"):
        (p.b.scatter(x=p.a) + p.b.line()).render()
    result = p.scatter(p.a, p.b, x=p.a).render()
    assert len(result.axes[0].collections) == 2
    assert result.axes[0].get_xlabel() == "$" + p.a.ltx + "$"


def test_raw_error_values_are_captured_when_the_plot_is_created():
    error = np.array([0.5, 1.0])
    plot = plotting.errorbar([1, 2], yerr=error)
    error[:] = 9
    np.testing.assert_equal(plot.data[0].yerr, [0.5, 1.0])
