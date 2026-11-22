"""Scoped typography and patterned encodings for scientific figures."""

import json
from contextlib import contextmanager
from copy import copy
from pathlib import Path

from matplotlib import rc_context, rcParams
from matplotlib.container import ErrorbarContainer
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.legend_handler import HandlerTuple
from matplotlib.patches import Rectangle

ASSETS = Path(__file__).with_name("assets")
TOKENS = json.loads((ASSETS / "theme.json").read_text())
THEME_VERSION = TOKENS["style_version"]
COLORS = tuple(
    TOKENS["palette"][key] for key in TOKENS["series"]["color_order"]
)
HATCHES = tuple(TOKENS["series"]["hatches"])
LINESTYLES = tuple(TOKENS["series"]["linestyles"])
INK = TOKENS["palette"]["ink"]


@contextmanager
def style_context(profile="computer", overrides=None):
    """Apply a versioned profile while preserving the caller's rc settings."""
    preset = TOKENS["profiles"][profile]
    for name in ("regular", "bold"):
        fontManager.addfont(str(ASSETS / TOKENS["typography"][name]))
    family = FontProperties(
        fname=str(ASSETS / TOKENS["typography"]["regular"]),
    ).get_name()
    settings: dict = {
        "font.family": family,
        "font.size": preset["font_size"],
        "mathtext.fontset": "cm",
        "text.usetex": False,
        "axes.titlesize": preset["title_size"],
        "axes.titleweight": "bold",
        "axes.titlecolor": TOKENS["palette"]["title"],
        "axes.edgecolor": INK,
        "axes.linewidth": preset["stroke"],
        "hatch.linewidth": preset["hatch_linewidth"],
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.dpi": preset["dpi"],
        "svg.fonttype": "path",
    }
    settings.update(TOKENS["graph_rc"])
    settings.update(overrides or {})
    with rc_context():
        rcParams.update(settings)
        yield


def pattern_key(color, hatch):
    """Overlay a coloured pattern and a neutral visible legend boundary."""
    return (
        Rectangle(
            (0, 0),
            1,
            1,
            facecolor="white",
            edgecolor=color,
            hatch=hatch,
            linewidth=0,
        ),
        Rectangle((0, 0), 1, 1, fill=False, edgecolor=INK, linewidth=0.7),
    )


def legend(ax, handles, labels):
    """Retain first-seen labels, with boxed keys for patterned quantities."""
    unique: dict = {}
    for label, original in zip(labels, handles):
        handle = _legend_handle(original)
        if label in unique:
            previous = unique[label]
            first = previous if isinstance(previous, tuple) else (previous,)
            second = handle if isinstance(handle, tuple) else (handle,)
            unique[label] = (*first, *second)
        else:
            unique[label] = handle
    if unique:
        ax.legend(
            list(unique.values()),
            list(unique),
            handler_map={tuple: HandlerTuple(ndivide=1, pad=0)},
        )


def _legend_handle(handle):
    """Give interval keys a visible path without connecting observations."""
    if isinstance(handle, ErrorbarContainer) and handle.lines[0] is not None:
        line = copy(handle.lines[0])
        if line.get_linestyle() == "None":
            line.set_linestyle("-")
        return ErrorbarContainer(
            (line, *handle.lines[1:]),
            has_xerr=handle.has_xerr,
            has_yerr=handle.has_yerr,
        )
    return handle
