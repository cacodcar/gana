"""Composable two-dimensional scientific plots for arrays and Gana quantities.

CHECK_INDICES enables semantic index validation by default. Set it to False
on this module to skip those checks and let Matplotlib validate artist shapes.
"""

from .api import (
    ElementPlots,
    PlotMethods,
    area,
    band,
    bar,
    column,
    errorbar,
    grid,
    line,
    row,
    scatter,
    stacked,
)
from .data import Series, Snapshot, snapshot
from .plot import Layout, Plot, RenderedPlot
from .theme import THEME_VERSION, style_context

CHECK_INDICES = True

__all__ = [
    "CHECK_INDICES",
    "THEME_VERSION",
    "ElementPlots",
    "Layout",
    "Plot",
    "PlotMethods",
    "RenderedPlot",
    "Series",
    "Snapshot",
    "area",
    "band",
    "bar",
    "column",
    "errorbar",
    "grid",
    "line",
    "row",
    "scatter",
    "snapshot",
    "stacked",
    "style_context",
]
