"""Detached adapter records preserve identity through Gana composition."""

from dataclasses import replace

import numpy as np
import pytest
from matplotlib import pyplot as plt

from gana import I, P, Prg, V, inf, sigma
from gana.plotting import (
    Series,
    band,
    column,
    line,
    scatter,
    snapshot,
    stacked,
)


def test_snapshot_retains_complete_coordinates_and_selected_history():
    p = Prg()
    p.t = I(size=3)
    p.v = V(p.t)
    p.c = p.v >= [1, 2, 3]
    p.cost = inf(sigma(p.v))
    p.opt()
    state = p.v._symbol_storage.owner
    before = (len(state.states), len(state.cache))
    saved = snapshot(p.v)
    assert saved.coordinates == tuple(p.v.map)
    assert saved.values == (1, 2, 3)
    assert saved.n_sol == 0
    assert before == (len(state.states), len(state.cache))
    p.more = p.v >= [4, 5, 6]
    p.opt()
    assert snapshot(p.v, n_sol=1).values == (4, 5, 6)
    assert saved.values == (1, 2, 3)
    assert snapshot([3, None]).coordinates == (0, 1)
    p.a = P(p.t, _=[1, 0, 3])
    assert snapshot(p.a).n_sol is None


def test_series_input_copies_values_bounds_and_errors():
    values, bounds, errors = [2, 3], [1, 2], np.array([0.2, 0.4])
    source = Series(
        [0, 1],
        values,
        ["a", "b"],
        domain=("time",),
        key=("wind",),
        label="Wind",
        lower=bounds,
        upper=(3, 4),
        yerr=errors,
        unit="MWh",
        n_sol=2,
    )
    description = band(source, lower=source.lower, upper=source.upper) + line(
        source
    )
    values[0] = 99
    bounds[0] = 99
    errors[0] = 99
    assert description.data[0].values == (2, 3)
    assert description.data[0].lower == (1, 2)
    np.testing.assert_equal(description.data[0].yerr, [0.2, 0.4])
    assert description.data[0].unit == "MWh"
    assert description.data[0].n_sol == 2
    result = description.render()
    np.testing.assert_equal(result.axes[0].lines[0].get_ydata(), [2, 3])
    plt.close(result.figure)


def test_adapter_coordinates_and_units_are_checked_across_layers_and_panels():
    a = Series((0, 1), (1, 2), ("a", "b"), domain=("hour",), unit="MWh")
    b = replace(a, coordinates=("b", "a"))
    with pytest.raises(ValueError, match="coordinate order"):
        stacked(a, b).render()
    with pytest.raises(ValueError, match="coordinate order"):
        band(a, lower=b, upper=(3, 4))
    with pytest.raises(ValueError, match="index domains"):
        (line(a) + line(replace(a, domain=("day",)))).render()
    with pytest.raises(ValueError, match="matching units"):
        (line(a) + line(replace(a, unit="USD"))).render()
    with pytest.raises(ValueError, match="matching units"):
        column(line(a), line(replace(a, unit="USD")), sharey=True).render()
    with pytest.raises(ValueError, match="already define"):
        line(a, x=(1, 2))
    result = band(a, lower=replace(a, values=(0, 1)), upper=(3, 4)).render()
    plt.close(result.figure)


def test_export_preserves_explicit_font_settings(tmp_path):
    path = line([1, 2]).save(
        tmp_path / "editable.svg", rc={"svg.fonttype": "none"}
    )
    assert "<text" in path.read_text()


def test_series_scatter_uses_matching_value_coordinates():
    y = Series((0, 1), (10, 20), ("a", "b"), domain=("hour",))
    x = replace(y, values=(2, 4), label="Cost", key=("cost",))
    result = scatter(y, x=x).render()
    np.testing.assert_equal(
        result.axes[0].collections[0].get_offsets(), [[2, 10], [4, 20]]
    )
    assert result.axes[0].get_xlabel() == "Cost"
    plt.close(result.figure)


def test_value_axes_and_bounds_preserve_original_coordinates():
    y = Series((0, 1), (2, 4), ("a", "b"), domain=("hour",), unit="MWh")
    x = replace(y, values=(10, 20), key=("cost",), unit="USD")
    bounds = replace(y, values=(1, 3))
    result = band(y, x=x, lower=bounds, upper=(3, 5)).render()
    assert result.data[0].x == (10, 20)
    plt.close(result.figure)
    with pytest.raises(ValueError, match="matching units"):
        band(y, lower=x, upper=(3, 5))
