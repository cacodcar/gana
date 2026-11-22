"""Plot descriptions compose before Matplotlib figures are created."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib import pyplot as plt

from .data import Series, checks_enabled, compatible, extract
from .render import panel_entries, render_panel
from .theme import THEME_VERSION, style_context


@dataclass(frozen=True)
class Layer:
    """A chart type and its detached profiles share one set of options."""

    chart: str
    series: tuple[Series, ...]
    options: dict = field(default_factory=dict)


@dataclass
class RenderedPlot:
    """
    A rendered figure exposes axes, plotted records and resolved settings.
    """

    figure: Any
    axes: tuple
    data: tuple[Series, ...]
    specification: Any
    theme_version: str = THEME_VERSION


class Plot:
    """A reusable chart description with explicit rendering and composition.

    Adding plots retains both descriptions and leaves the operands unchanged.
    Values are captured when the plot is constructed; later solves do not
    silently replace a figure's selected result.
    """

    def __init__(self, layers=(), **options):
        """Retain layers and figure options without opening a figure."""
        self.layers = tuple(layers)
        self.options = dict(options)

    def __add__(self, other):
        """Overlay another plot, rejecting conflicting figure settings."""
        if not isinstance(other, Plot):
            return NotImplemented
        options = dict(self.options)
        for key, value in other.options.items():
            if key in options and options[key] != value:
                message = f"Conflicting {key!r}; use with_options() to resolve"
                raise ValueError(message)
            options[key] = value
        return Plot((*self.layers, *other.layers), **options)

    def with_options(self, **options):
        """Return a new description with explicitly replaced figure options."""
        return Plot(self.layers, **(self.options | options))

    @property
    def data(self):
        """Expose detached plotted values and source coordinates in order."""
        return tuple(
            series for layer in self.layers for series in layer.series
        )

    def _panels(self):
        panels = dict.fromkeys(series.panel for series in self.data)
        return tuple(panels) or ((),)

    def _validate(self):
        if not checks_enabled():
            return
        panels = [
            tuple(dict.fromkeys(s.panel for s in layer.series))
            for layer in self.layers
            if layer.series
        ]
        if any(panel != panels[0] for panel in panels[1:]):
            message = "Combined plots require matching panel indices and order"
            raise ValueError(message)
        for panel in self._panels():
            _validate_panel(panel_entries(self.layers, panel))

    def render(self, ax=None, **options):
        """Render on new or supplied axes and return the figure and records."""
        return self._render(ax, self.options | options, {})

    def _render(self, ax, resolved, colors):
        self._validate()
        panels = self._panels()
        profile = resolved.get("profile", "computer")
        rc = dict(resolved.get("rc", {}))
        for key, setting in (
            ("font_size", "font.size"),
            ("usetex", "text.usetex"),
        ):
            if key in resolved:
                rc[setting] = resolved[key]
        with style_context(profile, rc):
            figure, axes = _axes(ax, len(panels), resolved)
            completed = False
            try:
                for panel, axis in zip(panels, axes):
                    render_panel(axis, self.layers, panel, resolved, colors)
                completed = True
            finally:
                if not completed and ax is None:
                    plt.close(figure)
        return RenderedPlot(
            figure, axes, self.data, Plot(self.layers, **resolved)
        )

    def show(self, **options):
        """Render and display this plot, returning the inspectable result."""
        result = self.render(**options)
        plt.show()
        return result

    def save(self, path, **options):
        """Export PDF, SVG or PNG at the selected physical figure size."""
        path = Path(path)
        if path.suffix.lower() not in {".pdf", ".svg", ".png"}:
            message = "Plot exports support PDF, SVG and PNG"
            raise ValueError(message)
        dpi = options.pop("dpi", None)
        result = self.render(**options)
        try:
            with style_context(
                result.specification.options.get("profile", "computer")
            ):
                result.figure.savefig(path, dpi=dpi)
        finally:
            plt.close(result.figure)
        return path


def _validate_panel(entries):
    if not entries:
        return
    first = entries[0][1]
    groups: dict[tuple, Series] = {}
    for layer, series in entries:
        compatible(first, series)
        if layer.chart in {"bar", "area"}:
            group = (layer.chart, layer.options.get("kind", "grouped"))
            previous = groups.setdefault(group, series)
            compatible(previous, series, aligned=True)


def _axes(ax, count, options):
    if ax is not None:
        axes = tuple(np.asarray(ax, dtype=object).reshape(-1))
        if len(axes) != count or any(
            a.figure is not axes[0].figure for a in axes
        ):
            message = "Supply one axis per panel, all belonging to one figure"
            raise ValueError(message)
        return axes[0].figure, axes
    width, height = options.get("fig_size", (6.4, 3.8 * count))
    figure, grid_axes = plt.subplots(
        count,
        1,
        figsize=(width, height),
        sharex=options.get("sharex", False),
        sharey=options.get("sharey", False),
        layout="constrained",
        squeeze=False,
    )
    return figure, tuple(grid_axes[:, 0])


FIGURE_OPTIONS = frozenset(
    {
        "title",
        "xlabel",
        "ylabel",
        "xlim",
        "ylim",
        "xscale",
        "yscale",
        "fig_size",
        "profile",
        "rc",
        "legend",
        "grid_alpha",
        "sharex",
        "sharey",
        "ticks",
        "tick_labels",
        "font_size",
        "usetex",
        "str_idx_lim",
        "x_ticks_lim",
    }
)
DATA_OPTIONS = frozenset(
    {
        "n_sol",
        "x",
        "series",
        "panel",
        "lower",
        "upper",
        "xerr",
        "yerr",
        "label",
    }
)
CHARTS = frozenset({"line", "scatter", "bar", "band", "errorbar", "area"})


def make_plot(chart, *sources, **options):
    """Construct every public entry point through the same data contract."""
    if chart not in CHARTS or not sources:
        message = "Choose a supported chart and supply at least one quantity"
        raise ValueError(message)
    figure = {k: options.pop(k) for k in tuple(options) if k in FIGURE_OPTIONS}
    data_options = {
        k: options.pop(k) for k in tuple(options) if k in DATA_OPTIONS
    }
    _validate_options(chart, options, data_options)
    records = tuple(
        s for source in sources for s in extract(source, **data_options)
    )
    return Plot((Layer(chart, records, options),), **figure)


def _validate_options(chart, options, data_options):
    mode = options.get("kind", "grouped" if chart == "bar" else "simple")
    if chart in {"bar", "area"} and mode not in {
        "simple",
        "grouped",
        "stacked",
    }:
        message = "kind must be 'simple', 'grouped' or 'stacked'"
        raise ValueError(message)
    if chart == "band" and any(
        data_options.get(k) is None for k in ("lower", "upper")
    ):
        message = "A band requires explicit lower and upper bounds"
        raise ValueError(message)


class Layout:
    """An explicit grid of plot descriptions with optional shared axes."""

    def __init__(self, rows, **options):
        """
        Retain a rectangular grid; use None for an intentionally empty cell.
        """
        self.rows = tuple(tuple(row) for row in rows)
        if (
            not self.rows
            or not self.rows[0]
            or any(len(r) != len(self.rows[0]) for r in self.rows)
        ):
            message = "A layout requires a nonempty rectangular grid"
            raise ValueError(message)
        self.options = dict(options)

    def _validate_shared(self, options):
        if not checks_enabled() or not options.get("sharex"):
            return
        records = [
            s
            for row in self.rows
            for plot in row
            if plot is not None
            for s in plot.data
        ]
        for series in records[1:]:
            compatible(records[0], series)

    def _draw_cells(self, axes, options):
        records = []
        colors: dict[tuple, int] = {}
        for plots, row_axes in zip(self.rows, axes):
            for plot, axis in zip(plots, row_axes):
                if plot is None:
                    axis.set_visible(False)
                else:
                    result = plot._render(axis, plot.options | options, colors)
                    records.extend(result.data)
        return tuple(records)

    def render(self, **options):
        """Render child plots into one figure with shared category styles."""
        options = self.options | options
        self._validate_shared(options)
        with style_context(
            options.get("profile", "computer"), options.get("rc")
        ):
            figure, axes = plt.subplots(
                len(self.rows),
                len(self.rows[0]),
                squeeze=False,
                figsize=options.get(
                    "fig_size", (6.4 * len(self.rows[0]), 3.8 * len(self.rows))
                ),
                sharex=options.get("sharex", False),
                sharey=options.get("sharey", False),
                layout="constrained",
            )
            completed = False
            try:
                records = self._draw_cells(axes, options)
                completed = True
            finally:
                if not completed:
                    plt.close(figure)
        return RenderedPlot(
            figure, tuple(axes.flat), records, Layout(self.rows, **options)
        )

    show = Plot.show
    save = Plot.save
