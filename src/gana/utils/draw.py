"""Plotting Utilities"""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib import pyplot as plt
from matplotlib import rc

if TYPE_CHECKING:
    from ..sets.parameter import P
    from ..sets.variable import V


def draw(
    element: V | P,
    data: list[float] | None = None,
    kind: str = "line",
    font_size: float = 16,
    fig_size: tuple[float, float] = (12, 6),
    linewidth: float = 0.7,
    color: str = "blue",
    grid_alpha: float = 0.3,
    usetex: bool = True,
    str_idx_lim: int = 10,
):
    """
    Plot the variable set

    :param kind: Type of plot ['line', 'bar']. Defaults to 'line'.
    :type kind: str, optional
    :param font_size: Font size for the plot. Defaults to 16.
    :type font_size: float, optional
    :param fig_size: Size of the figure. Defaults to (12, 6).
    :type fig_size: tuple[float, float], optional
    :param linewidth: Width of the line in the plot. Defaults to 0.7.
    :type linewidth: float, optional
    :param color: Color of the line in the plot. Defaults to 'blue'.
    :type color: str, optional
    :param grid_alpha: Transparency of the grid lines. Defaults to 0.3.
    :type grid_alpha: float, optional
    :param usetex: Use LaTeX for text rendering. Defaults to True.
    :type usetex: bool, optional
    :param str_idx_lim: Limit for string indices display. Defaults to 10.
    :type str_idx_lim: int, optional
    """

    ax = plt.subplots(figsize=fig_size)[1]

    # the values are the y-axis
    y = data

    _len = len(y)

    # the indices are the x-axis
    if _len <= str_idx_lim:
        x = [str(idx) for idx in element.map]
    else:
        x = list(range(len(y)))

    if usetex:
        rc(
            "font",
            **{"family": "serif", "serif": ["Computer Modern"], "size": font_size},
        )
        rc("text", usetex=usetex)
    else:
        rc("font", **{"size": font_size})

    if kind == "line":
        ax.plot(x, y, linewidth=linewidth, color=color)

    elif kind == "bar":
        ax.bar(x, y, linewidth=linewidth, color=color)

    ax.set_title(
        rf"${element.latex()}$",
    )
    ax.set_ylabel(r"Values")
    ax.set_xlabel(r"Indices")
    ax.grid(alpha=grid_alpha)

    if _len <= str_idx_lim:
        ax.set_xticks(x)
        ax.set_xticklabels(
            [
                rf"${tuple([idx.ltx for idx in index])}$".replace("'", "").replace(
                    "\\", ""
                )
                for index in element.map
            ]
        )

    plt.rcdefaults()
    return plt
