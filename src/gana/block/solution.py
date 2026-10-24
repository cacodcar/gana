"""Solution"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from matplotlib import pyplot as plt
from matplotlib import rc

from ..backends.native.results import _SolutionColumn, update_solution
from ..sets.index import I
from ..sets.variable import V


@dataclass
class Solution:
    """A State with its variables filled in

    :param name: Name of the solution
    :type name: str
    """

    name: str = " "

    def __post_init__(self):

        self._: dict[str, dict[str, list]] = {}

    def asdict(self):
        """Return the solution as a dictionary"""
        return {v: values["values"] for v, values in self._.items()}

    def update(self, variable_sets: Sequence[V], n_sol: int = 0):
        """
        Read either a legacy list or a lazy registry into solution output.
        """
        if update_solution(self, variable_sets, n_sol):
            return
        for variable in variable_sets:
            self._add_variable(variable, n_sol)

    def _add_variable(self, variable: V | _SolutionColumn, number: int):
        """
        Append one output record from a scalar or lightweight native adapter.
        """
        parent = variable.parent
        if parent is None:
            message = "Solution output requires a registered scalar variable"
            raise ValueError(message)
        name = parent.name
        if name not in self._:
            self._[name] = {
                key: []
                for key in (
                    "latex",
                    "index_latex",
                    "positions",
                    "n",
                    "values",
                    "index",
                )
            }
        record = self._[name]
        record["latex"].append(variable.latex())
        record["index_latex"].append(r"$" + variable.index_ltx + r"$")
        record["positions"].append(variable.pos)
        record["n"].append(variable.n)
        record["values"].append(variable.X[number] if variable.X else None)
        record["index"].append(self._index_metadata(variable.index))

    @staticmethod
    def _index_metadata(index):
        """
        Retain the established nested coordinate description for plotting.
        """
        return {
            idx.name: {par.name: pos for par, pos in zip(idx.parent, idx.pos)}
            for idx in index
            if isinstance(idx, I)
        }

    def __call__(self, variable: V):
        """Return scalar metadata or lists of metadata for a selection.

        Scalar members have a parent and an integer position within it;
        selections retain those original member positions and row order.
        """

        if variable.parent:
            position = cast("int", variable.pos)
            return {
                "latex": self._[variable.parent.name]["latex"][position],
                "index_latex": r"$"
                + self._[variable.parent.name]["index_latex"][position]
                + r"$",
                "positions": self._[variable.parent.name]["positions"][
                    position
                ],
                "n": self._[variable.parent.name]["n"][position],
                "values": self._[variable.parent.name]["values"][position],
                "index": self._[variable.parent.name]["index"][position],
            }

        # Each field collects its own metadata kind in the same row order.
        _return: dict[str, list[object]] = {
            "latex": [],
            "index_latex": [],
            "positions": [],
            "n": [],
            "values": [],
            "index": [],
        }
        for var in variable:
            # Iteration supplies scalar members, including for selections.
            parent = cast("V", var.parent)
            position = cast("int", var.pos)
            _return["latex"].append(self._[parent.name]["latex"][position])
            _return["index_latex"].append(
                self._[parent.name]["index_latex"][position],
            )
            _return["positions"].append(
                self._[parent.name]["positions"][position],
            )
            _return["n"].append(self._[parent.name]["n"][position])
            _return["values"].append(
                self._[parent.name]["values"][position],
            )
            _return["index"].append(self._[parent.name]["index"][position])
        return _return

    def draw(
        self,
        variable: V,
        kind: str = "line",
        font_size: float = 16,
        fig_size: tuple[float, float] = (10, 6),
        linewidth: float = 0.7,
        color: str = "blue",
        grid_alpha: float = 0.3,
        usetex: bool = True,
        x_ticks_lim: int = 20,
    ):
        """Plot the variable set

        :param variable: The variable to plot
        :type variable: V
        :param kind: Type of plot ['line', 'bar'], defaults to 'line'
        :type kind: str, optional
        :param font_size: Font size for the plot, defaults to 16
        :type font_size: float, optional
        :param fig_size: Size of the figure, defaults to (12, 6)
        :type fig_size: tuple[float, float], optional
        :param linewidth: Width of the line in the plot, defaults to 0.7
        :type linewidth: float, optional
        :param color: Color of the line in the plot, defaults to 'blue'
        :type color: str, optional
        :param grid_alpha: Transparency of the grid lines, defaults to 0.3
        :type grid_alpha: float, optional
        :param usetex: Use LaTeX for text rendering, defaults to True
        :type usetex: bool, optional
        :param x_ticks_lim: Maximum number of x-ticks to display, defaults to
            20
        :type x_ticks_lim: int, optional
        """

        data = self(variable)

        hold = self._held_indices(data["index"])

        ax = plt.subplots(figsize=fig_size)[1]

        # the indices are the x-axis
        x = range(len(data["values"]))
        # the values are the y-axis
        y = data["values"]

        if usetex:
            rc(
                "font",
                **{
                    "family": "serif",
                    "serif": ["Computer Modern"],
                    "size": font_size,
                },
            )
            rc("text", usetex=usetex)
        else:
            rc("font", **{"size": font_size})

        if kind == "line":
            ax.plot(x, y, linewidth=linewidth, color=color)

        elif kind == "bar":
            ax.bar(x, y, linewidth=linewidth, color=color)

        title = rf"${variable.tag or variable.name}$"

        if hold:
            title += " (" + ", ".join(str(item) for item in hold) + ")"

        ax.set_title(title)
        ax.set_ylabel(r"Values")

        ax.set_xlabel(r"Indices")
        ax.grid(alpha=grid_alpha)

        if len(x) <= x_ticks_lim:
            ax.set_xticks(x)

            ax.set_xticklabels(self._plot_tick_labels(data, hold))

        plt.rcdefaults()

    @staticmethod
    def _held_indices(indices):
        """Find fixed coordinates by position, retaining first-seen order.

        The plotting metadata uses ordered coordinate names as dictionary
        keys. Compare those names, not their nested position descriptions.
        """
        unique: dict[int, list] = {}
        for index in indices:
            for position, name in enumerate(index):
                names = unique.setdefault(position, [])
                if name not in names:
                    names.append(name)
        return [names[0] for names in unique.values() if len(names) == 1]

    @staticmethod
    def _plot_tick_labels(data, hold):
        """Strip fixed-coordinate names with the existing LaTeX convention."""
        labels = []
        for original, index in zip(data["index_latex"], data["index"]):
            latex = original
            for name in index:
                if name in hold:
                    latex = latex.replace(name + ",", "").replace(name, "")
            labels.append(latex)
        return labels

    def line(self, **kwargs):
        """Alias for plot with kind='line'"""
        self.draw(kind="line", **kwargs)

    def bar(self, **kwargs):
        """Alias for plot with kind='bar'"""
        self.draw(kind="bar", **kwargs)

    def __getitem__(self, item):
        return self._[item]
