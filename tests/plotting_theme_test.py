"""Category identities and interval keys survive changes in presentation."""

from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from gana import plotting


def test_line_identity_survives_panel_subsets_and_explicit_overrides():
    solar, wind = [0, 3, 1], [2, 1, 2]
    combined = plotting.line(solar) + plotting.line(wind)
    layout = plotting.row(combined, plotting.line(wind))
    result = layout.render()
    try:
        first, second = result.axes[0].lines
        repeated = result.axes[1].lines[0]
        assert first.get_linestyle() != second.get_linestyle()
        assert second.get_linestyle() == repeated.get_linestyle()
        assert second.get_color() == repeated.get_color()
    finally:
        plt.close(result.figure)
    explicit = plotting.line(wind, linestyle=":", linewidth=2).render()
    try:
        assert explicit.axes[0].lines[0].get_linestyle() == ":"
        assert explicit.axes[0].lines[0].get_linewidth() == 2
    finally:
        plt.close(explicit.figure)


def test_interval_key_path_does_not_connect_observations():
    plot = plotting.errorbar([1, 3, 2], yerr=0.4, color="gold", label="Data")
    result = plot.render()
    try:
        axis = result.axes[0]
        data_line, _, intervals = axis.containers[0].lines
        assert data_line.get_linestyle() == "None"
        assert len(intervals[0].get_segments()) == 3
        keys = axis.get_legend().findobj(Line2D)
        assert any(
            key.get_linestyle() == "-" and key.get_color() == "gold"
            for key in keys
        )
    finally:
        plt.close(result.figure)
