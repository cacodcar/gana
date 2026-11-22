"""Object and array entry points construct the same plot descriptions."""

from .plot import Layout, make_plot


def line(*sources, **options):
    """
    Describe one or more profiles; step='pre', 'post' or 'mid' is optional.
    """
    return make_plot("line", *sources, **options)


def scatter(*sources, **options):
    """Describe observations; x may be coordinates or an indexed quantity."""
    return make_plot("scatter", *sources, **options)


def bar(*sources, kind="grouped", **options):
    """Describe simple, grouped or signed stacked bars."""
    return make_plot("bar", *sources, kind=kind, **options)


def stacked(*sources, **options):
    """Describe stacked bars through the ordinary bar implementation."""
    return bar(*sources, kind="stacked", **options)


def band(*sources, lower, upper, **options):
    """Describe supplied lower and upper bounds without estimating them."""
    return make_plot("band", *sources, lower=lower, upper=upper, **options)


def errorbar(*sources, **options):
    """Describe supplied xerr/yerr deviations around observed values."""
    return make_plot("errorbar", *sources, **options)


def area(*sources, kind="simple", **options):
    """Describe patterned area profiles, optionally with signed stacking."""
    return make_plot("area", *sources, kind=kind, **options)


def row(*plots, **options):
    """Arrange single-panel plots horizontally."""
    return Layout((plots,), **options)


def column(*plots, **options):
    """Arrange single-panel plots vertically."""
    return Layout(tuple((plot,) for plot in plots), **options)


def grid(rows, **options):
    """Arrange single-panel plots in an explicit rectangular grid."""
    return Layout(rows, **options)


class PlotMethods:
    """
    Programs collect quantities while sharing the public chart constructors.
    """

    def _plot_arguments(self, sources, options):
        return sources, options

    def _plot(self, chart, sources, options):
        sources, options = self._plot_arguments(sources, options)
        return make_plot(chart, *sources, **options)

    def line(self, *sources, **options):
        """Return a line plot; n_sol selects a stored variable solution."""
        return self._plot("line", sources, options)

    def scatter(self, *sources, **options):
        """
        Return a scatter plot with shared axis mappings and style options.
        """
        return self._plot("scatter", sources, options)

    def bar(self, *sources, kind="grouped", **options):
        """Return bars with kind='simple', 'grouped' or 'stacked'."""
        return self._plot("bar", sources, {"kind": kind, **options})

    def stacked(self, *sources, **options):
        """Return the same description as bar(..., kind='stacked')."""
        return self.bar(*sources, kind="stacked", **options)

    def band(self, *sources, lower, upper, **options):
        """
        Return explicit interval bounds; the central curve is a line layer.
        """
        return self._plot(
            "band", sources, {"lower": lower, "upper": upper, **options}
        )

    def errorbar(self, *sources, **options):
        """Return observations with supplied xerr and/or yerr deviations."""
        return self._plot("errorbar", sources, options)

    def area(self, *sources, kind="simple", **options):
        """Return patterned areas, with optional kind='stacked'."""
        return self._plot("area", sources, {"kind": kind, **options})


class ElementPlots(PlotMethods):
    """
    An element supplies itself and retains legacy positional style options.
    """

    def _plot_arguments(self, sources, options):
        names = (
            "font_size",
            "fig_size",
            "linewidth",
            "color",
            "grid_alpha",
            "usetex",
            "str_idx_lim",
        )
        if len(sources) > len(names):
            message = "Too many positional plotting options"
            raise TypeError(message)
        return (self,), dict(zip(names, sources)) | options
