"""Artist geometry, composition and exports preserve the plotted quantities."""

from pathlib import Path

import matplotlib as mpl
import numpy as np
import pytest
from matplotlib import pyplot as plt
from matplotlib.colors import to_rgba

from gana import I, P, Prg, plotting
from gana.plotting.theme import COLORS, TOKENS


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def model():
    p = Prg()
    p.t = I(size=3)
    p.a = P(p.t, _=[2, -3, 0])
    p.b = P(p.t, _=[4, -1, 5])
    return p


def test_signed_stacks_alias_and_mixed_line():
    p = model()
    plot = p.stacked(p.a, p.b) + p.line(p.a)
    result = plot.render()
    bars = result.axes[0].patches
    assert [b.get_y() for b in bars] == [0, 0, 0, 2, -3, 0]
    assert [b.get_height() for b in bars] == [2, -3, 0, 4, -1, 5]
    assert [s.values for s in p.bar(p.a, p.b, kind="stacked").data] == [
        s.values for s in p.stacked(p.a, p.b).data
    ]
    np.testing.assert_equal(result.axes[0].lines[0].get_ydata(), [2, -3, 0])
    assert p.a.stacked().layers[0].options["kind"] == "stacked"


def test_missing_stacked_contribution_propagates_unavailable_total():
    plot = plotting.stacked([1, None, -2], [2, 4, -3])
    bars = plot.render().axes[0].patches
    np.testing.assert_equal([b.get_y() for b in bars[3:]], [1, np.nan, -2])
    assert bars[-1].get_y() + bars[-1].get_height() == -5


def test_patterns_have_white_interiors_and_boxed_legend_keys():
    p = model()
    result = p.bar(p.a, p.b).render()
    first = result.axes[0].patches[0]
    assert first.get_facecolor() == to_rgba("white")
    assert first.get_edgecolor() == to_rgba(COLORS[0])
    assert len(first.get_hatch()) == 4
    assert len(result.axes[0].collections) == 2
    assert result.axes[0].get_legend() is not None


def test_area_and_uncertainty_envelopes_have_exact_bounds():
    p = model()
    area = p.area(p.a, p.b, kind="stacked").render()
    # Each area contributes a patterned polygon and a neutral outline.
    upper_path = area.axes[0].collections[2].get_paths()[0].vertices
    assert max(upper_path[:, 1]) == 6
    assert min(upper_path[:, 1]) == -4
    band = p.a.band(lower=[1, -4, -1], upper=[3, -2, 1]) + p.a.line()
    result = band.render()
    path = result.axes[0].collections[0].get_paths()[0].vertices
    assert min(path[:, 1]) == -4
    assert max(path[:, 1]) == 3
    assert len(result.axes[0].lines) == 1
    assert len(p.a.area().data) == 1


def test_errorbars_preserve_asymmetric_deviations():
    p = model()
    result = p.errorbar(p.a, yerr=[[1, 2, 1], [2, 4, 3]], xerr=0.2).render()
    segments = result.axes[0].collections[-1].get_segments()
    np.testing.assert_equal(segments[0], [[0, 1], [0, 4]])
    assert len(p.a.errorbar(yerr=1).render().axes) == 1


def test_profiles_restore_rc_settings_and_accept_supplied_axes(tmp_path):
    p = model()
    with mpl.rc_context({"font.size": 17, "axes.facecolor": "ivory"}):
        original = dict(mpl.rcParams)
        figure, axis = plt.subplots()
        result = p.a.line(step="post", title="Output").render(ax=axis)
        assert result.figure is figure
        assert result.axes == (axis,)
        assert result.axes[0].lines[0].get_drawstyle() == "steps-post"
        assert dict(mpl.rcParams) == original
        for profile in ("print", "computer", "slides"):
            file = tmp_path / (profile + ".svg")
            p.a.bar().save(file, profile=profile, fig_size=(3.5, 2.5))
            assert file.stat().st_size > 1000
            assert dict(mpl.rcParams) == original
    fresh = p.a.line(title="Output").render()
    assert fresh.axes[0].title.get_color() == TOKENS["palette"]["title"]


def test_exports_and_explicit_show_return_inspectable_results(
    tmp_path, monkeypatch
):
    plot = plotting.line([1, 2, 3], label="Series")
    called = []
    monkeypatch.setattr(plt, "show", lambda: called.append(True))
    result = plot.show()
    assert called == [True]
    assert result.data == plot.data
    for extension in ("png", "pdf", "svg"):
        path = tmp_path / ("plot." + extension)
        assert plot.save(path, profile="print", dpi=150) == path
        assert path.stat().st_size > 1000
    with pytest.raises(ValueError, match="PDF, SVG and PNG"):
        plot.save(tmp_path / "plot.gif")
    with pytest.raises(FileNotFoundError):
        plot.save(tmp_path / "missing" / "plot.pdf")


def test_layouts_share_axes_and_export(tmp_path, monkeypatch):
    p = model()
    line = p.a.line()
    bars = p.b.bar()
    row = plotting.row(line, bars, sharey=True).render()
    assert row.axes[0].get_shared_y_axes().joined(*row.axes)
    column = plotting.column(line, bars, sharex=True).render()
    assert column.axes[0].get_shared_x_axes().joined(*column.axes)
    layout = plotting.grid([[line, bars], [None, line]], profile="print")
    result = layout.render()
    assert len(result.axes) == 4
    assert not result.axes[2].get_visible()
    monkeypatch.setattr(plt, "show", lambda: None)
    assert len(layout.show().axes) == 4
    assert Path(layout.save(tmp_path / "panels.pdf")).exists()


def test_global_figure_conflicts_require_an_explicit_choice():
    p = model()
    first = p.a.line(title="First")
    second = p.b.line(title="Second")
    with pytest.raises(ValueError, match="Conflicting 'title'"):
        first + second
    combined = first + second.with_options(title="First")
    assert combined.render().axes[0].get_title() == "First"
    with pytest.raises(TypeError):
        first + 1


def test_invalid_requests_raise_useful_errors():
    p = model()
    with pytest.raises(ValueError, match="at least one quantity"):
        p.bar()
    with pytest.raises(ValueError, match="kind must be"):
        p.a.bar(kind="unknown")
    with pytest.raises(ValueError, match="explicit lower and upper"):
        p.band(p.a, lower=None, upper=None)
    with pytest.raises(ValueError, match="lower bounds"):
        p.a.band(lower=2, upper=1).render()
    with pytest.raises(ValueError, match="rectangular grid"):
        plotting.grid([[p.a.line()], []])
    figure, axes = plt.subplots(2)
    with pytest.raises(ValueError, match="one axis per panel"):
        p.a.line().render(ax=axes)
    plt.close(figure)


def test_legacy_style_arguments_and_plain_array_entry_points():
    p = model()
    result = p.a.line(15, (5, 3), 2, "red", 0, False, 10).render()
    assert result.axes[0].lines[0].get_color() == "red"
    assert result.axes[0].lines[0].get_linewidth() == 2
    assert tuple(result.figure.get_size_inches()) == (5, 3)
    with pytest.raises(TypeError, match="Too many positional"):
        p.a.bar(*range(8))
    assert (
        len(plotting.scatter([1, 3], x=[2, 4]).render().axes[0].collections)
        == 1
    )
    assert (
        len(plotting.band([1, 2], lower=[0, 1], upper=[2, 3]).render().axes)
        == 1
    )
    assert len(plotting.errorbar([1, 2], yerr=0.5).render().axes) == 1
    assert len(plotting.area([1, 2]).render().axes) == 1


def test_layout_keeps_category_colors_across_different_subsets():
    p = model()
    result = plotting.row(p.line(p.a, p.b), p.b.line()).render()
    assert (
        result.axes[0].lines[1].get_color()
        == result.axes[1].lines[0].get_color()
    )


def test_failed_render_restores_style_and_closes_its_figure():
    p = model()
    before = plt.get_fignums()
    with mpl.rc_context({"font.size": 19}):
        with pytest.raises(ValueError, match="lower bounds"):
            p.a.band(lower=3, upper=2).render()
        assert mpl.rcParams["font.size"] == 19
    assert plt.get_fignums() == before


def test_inline_arrays_keep_distinct_styles_and_reused_arrays_share_styles():
    plot = plotting.line([1, 2], label="first") + plotting.line(
        [3, 4],
        label="second",
    )
    result = plot.render()
    assert (
        result.axes[0].lines[0].get_color()
        != result.axes[0].lines[1].get_color()
    )
    values = [1, 2]
    reused = plotting.line(values) + plotting.scatter(values)
    assert reused.data[0].key == reused.data[1].key


def test_shared_axis_layout_checks_domains_and_cleans_up_errors(monkeypatch):
    p = model()
    p.other = I(size=3)
    p.c = P(p.other, _=[7, 8, 9])
    layout = plotting.row(p.a.line(), p.c.line(), sharex=True)
    with pytest.raises(ValueError, match="index domains"):
        layout.render()
    monkeypatch.setattr(plotting, "CHECK_INDICES", False)
    assert len(layout.render().axes) == 2
    before = plt.get_fignums()
    bad = plotting.row(p.a.line(), p.a.band(lower=2, upper=1))
    with pytest.raises(ValueError, match="lower bounds"):
        bad.render()
    assert plt.get_fignums() == before
