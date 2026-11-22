"""Compatibility drawing entry point backed by the shared plot renderer."""

from matplotlib import pyplot as plt

from ..plotting.data import Series
from ..plotting.plot import Layer, Plot


def draw(
    element,
    data=None,
    kind="line",
    font_size=16,
    fig_size=(12, 6),
    linewidth=0.7,
    color="blue",
    grid_alpha=0.3,
    usetex=True,
    str_idx_lim=10,
):
    """Render immediately and retain the historical pyplot return value.

    New element methods return reusable Plot descriptions. This wrapper keeps
    positional flattened coordinates for existing direct draw callers.
    """
    if data is None:
        message = "Plot data is required"
        raise TypeError(message)
    x = tuple(range(len(data)))
    options = {
        "title": rf"${element.latex()}$",
        "fig_size": fig_size,
        "grid_alpha": grid_alpha,
        "legend": False,
        "rc": {"font.size": font_size, "text.usetex": usetex},
    }
    if len(data) <= str_idx_lim:
        options["ticks"] = x
        options["tick_labels"] = [
            "$" + ",".join(str(idx.ltx) for idx in index) + "$"
            for index in element.map
        ]
    chart = kind if kind in {"line", "bar"} else "empty"
    record = Series(x, tuple(data), x)
    Plot(
        (Layer(chart, (record,), {"color": color, "linewidth": linewidth}),),
        **options,
    ).render()
    return plt
