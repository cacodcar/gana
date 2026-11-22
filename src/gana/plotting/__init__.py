"""Composable two-dimensional scientific plots for arrays and Gana quantities.

CHECK_INDICES enables semantic index validation by default. Set it to False
on this module to skip those checks and let Matplotlib validate artist shapes.
"""

from .api import (
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
from .data import Series
from .plot import Layout, Plot, RenderedPlot
from .theme import THEME_VERSION, style_context

CHECK_INDICES = True

__all__ = [
    "CHECK_INDICES",
    "THEME_VERSION",
    "Layout",
    "Plot",
    "RenderedPlot",
    "Series",
    "area",
    "band",
    "bar",
    "column",
    "errorbar",
    "grid",
    "line",
    "row",
    "scatter",
    "stacked",
    "style_context",
]
