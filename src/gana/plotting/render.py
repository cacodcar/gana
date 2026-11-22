"""
Matplotlib artists consume the same detached profiles for every entry point.
"""

from collections import Counter

import numpy as np
from matplotlib.collections import LineCollection

from .theme import COLORS, HATCHES, INK, legend, pattern_key


def render_panel(ax, layers, panel, settings, colors):
    """
    Resolve category styles once and draw each layer in composition order.
    """
    entries = panel_entries(layers, panel)
    counts = Counter(_group(layer) for layer, _ in entries)
    positions: Counter = Counter()
    stacks: dict = {}
    handles, labels = [], []
    for layer, series in entries:
        number = colors.setdefault(series.key, len(colors))
        style = dict(layer.options)
        style.setdefault("color", COLORS[number % len(COLORS)])
        style.setdefault("hatch", HATCHES[number % len(HATCHES)])
        group = _group(layer)
        style["offset"] = positions[group]
        style["count"] = counts[group]
        positions[group] += 1
        handle = _draw(ax, layer.chart, series, style, stacks, group)
        if series.label:
            handles.append(handle)
            labels.append(series.label)
    _decorate(ax, entries, settings)
    if settings.get("legend", True):
        legend(ax, handles, labels)


def panel_entries(layers, panel):
    """Select the layer/profile pairs belonging to one coordinate panel."""
    return [
        (layer, s)
        for layer in layers
        for s in layer.series
        if s.panel == panel
    ]


def _group(layer):
    return layer.chart, layer.options.get("kind", "grouped")


def _draw(ax, chart, series, style, stacks, group):
    if chart == "empty":
        return None
    x = series.x
    y = np.asarray(series.values, dtype=float)
    color = style["color"]
    width = style.get("linewidth", 1.2)
    if chart == "line":
        drawstyle = (
            "steps-" + style["step"] if style.get("step") else "default"
        )
        return ax.plot(
            x,
            y,
            color=color,
            linewidth=width,
            linestyle=style.get("linestyle", "-"),
            marker=style.get("marker"),
            drawstyle=drawstyle,
        )[0]
    if chart == "scatter":
        return ax.scatter(
            x,
            y,
            s=style.get("size", 28),
            marker=style.get("marker", "o"),
            facecolors="white",
            edgecolors=color,
            linewidths=width,
        )
    if chart == "errorbar":
        return ax.errorbar(
            x,
            y,
            xerr=series.xerr,
            yerr=series.yerr,
            color=color,
            linewidth=width,
            fmt=style.get("fmt", "o"),
            markerfacecolor="white",
            capsize=style.get("capsize", 3),
        )
    if chart == "bar":
        return _bar(ax, series, y, style, stacks, group)
    return _area(ax, chart, series, y, style, stacks, group)


def _numeric_x(ax, x):
    ax.xaxis.update_units(x)
    return np.asarray(ax.convert_xunits(x), dtype=float)


def _bottom(y, stacks, group, stacked):
    if not stacked:
        return np.zeros_like(y)
    positive, negative = stacks.setdefault(
        group, (np.zeros_like(y), np.zeros_like(y))
    )
    bottom = np.where(y >= 0, positive, negative).copy()
    # A missing contribution makes the subsequent cumulative total unavailable.
    positive += np.where(y >= 0, y, np.where(np.isnan(y), np.nan, 0))
    negative += np.where(y < 0, y, np.where(np.isnan(y), np.nan, 0))
    return bottom


def _bar(ax, series, y, style, stacks, group):
    mode = style.get("kind", "grouped")
    x = _numeric_x(ax, series.x)
    width = style.get("width", 0.8)
    if mode == "grouped":
        width /= style["count"]
        x = x + (style["offset"] - (style["count"] - 1) / 2) * width
    bottom = _bottom(y, stacks, group, mode == "stacked")
    bars = ax.bar(
        x,
        y,
        width=width,
        bottom=bottom,
        facecolor="white",
        edgecolor=style["color"],
        hatch=style["hatch"],
        linewidth=0,
    )
    outlines = []
    for bar in bars:
        left, low = bar.get_xy()
        right, high = left + bar.get_width(), low + bar.get_height()
        outlines.append(
            [
                (left, low),
                (left, high),
                (right, high),
                (right, low),
                (left, low),
            ]
        )
    ax.add_collection(
        LineCollection(
            outlines, colors=INK, linewidths=style.get("linewidth", 0.7)
        )
    )
    return pattern_key(style["color"], style["hatch"])


def _area(ax, chart, series, y, style, stacks, group):
    x = _numeric_x(ax, series.x)
    if chart == "band":
        lower = np.asarray(series.lower, dtype=float)
        upper = np.asarray(series.upper, dtype=float)
        if np.any(lower > upper):
            message = "Band lower bounds cannot exceed upper bounds"
            raise ValueError(message)
    else:
        lower = _bottom(y, stacks, group, style.get("kind") == "stacked")
        upper = lower + y
    shape = ax.fill_between(
        x,
        lower,
        upper,
        facecolor="white",
        edgecolor=style["color"],
        hatch=style["hatch"],
        linewidth=0,
        step=style.get("step"),
    )
    ax.add_collection(
        LineCollection(
            [path.vertices for path in shape.get_paths()],
            colors=INK,
            linewidths=style.get("linewidth", 0.7),
        )
    )
    return pattern_key(style["color"], style["hatch"])


def _decorate(ax, entries, settings):
    first = entries[0][1] if entries else None
    title = settings.get("title", "")
    if first is not None and first.panel_label:
        title = (
            f"{title} — {first.panel_label}" if title else first.panel_label
        )
    ax.set_title(title)
    ax.set_xlabel(settings.get("xlabel", first.xlabel if first else "Indices"))
    ax.set_ylabel(settings.get("ylabel", "Values"))
    for key in ("xlim", "ylim", "xscale", "yscale"):
        if key in settings:
            getattr(ax, "set_" + key)(settings[key])
    if "ticks" in settings:
        ax.set_xticks(settings["ticks"], labels=settings.get("tick_labels"))
    alpha = settings.get("grid_alpha", 0.15)
    if alpha:
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=alpha)
