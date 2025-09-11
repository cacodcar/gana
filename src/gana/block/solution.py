"""Solution"""

from dataclasses import dataclass

from ..sets.index import I
from ..sets.variable import V

try:
    from matplotlib import pyplot as plt
    from matplotlib import rc

    has_matplotlib = True

except ImportError:
    has_matplotlib = False


@dataclass
class Solution:
    """A State with its variables filled in"""

    name: str = " "

    def __post_init__(self):

        self._: dict[str, dict[str, list]] = {}

    def update(self, variable_sets: list[V], n_sol: int = 0):
        """Add variables to the solution"""
        for v in variable_sets:
            if v.parent.name not in self._:
                self._[v.parent.name] = {
                    'latex': [],
                    'index_latex': [],
                    'positions': [],
                    'n': [],
                    'values': [],
                    'index': [],
                }
            self._[v.parent.name]['latex'].append(v.latex())
            self._[v.parent.name]['index_latex'].append(r'$' + v.latex(True) + r'$')
            self._[v.parent.name]['positions'].append(v.pos)
            self._[v.parent.name]['n'].append(v.n)
            self._[v.parent.name]['values'].append(v.value[n_sol])
            self._[v.parent.name]['index'].append(
                {
                    idx.name: {par.name: pos for par, pos in zip(idx.parent, idx.pos)}
                    for idx in v.index
                    if isinstance(idx, I)
                }
            )

    def __call__(self, variable: V):

        if variable.parent:
            return {
                'latex': self._[variable.parent.name]['latex'][variable.pos],
                'index_latex': r'$'
                + self._[variable.parent.name]['index_latex'][variable.pos]
                + r'$',
                'positions': self._[variable.parent.name]['positions'][variable.pos],
                'n': self._[variable.parent.name]['n'][variable.pos],
                'values': self._[variable.parent.name]['values'][variable.pos],
                'index': self._[variable.parent.name]['index'][variable.pos],
            }

        _return = {
            'latex': [],
            'index_latex': [],
            'positions': [],
            'n': [],
            'values': [],
            'index': [],
        }
        for var in variable:
            _return['latex'].append(self._[var.parent.name]['latex'][var.pos])
            _return['index_latex'].append(
                self._[var.parent.name]['index_latex'][var.pos]
            )
            _return['positions'].append(self._[var.parent.name]['positions'][var.pos])
            _return['n'].append(self._[var.parent.name]['n'][var.pos])
            _return['values'].append(self._[var.parent.name]['values'][var.pos])
            _return['index'].append(self._[var.parent.name]['index'][var.pos])
        return _return

    def draw(
        self,
        variable: V,
        kind: str = 'line',
        font_size: float = 16,
        fig_size: tuple[float, float] = (10, 6),
        linewidth: float = 0.7,
        color: str = 'blue',
        grid_alpha: float = 0.3,
        usetex: bool = True,
        x_ticks_lim: int = 20,
    ):
        """Plot the variable set

        Args:
            kind (str, optional): Type of plot ['line', 'bar']. Defaults to 'line'.
            font_size (float, optional): Font size for the plot. Defaults to 16.
            fig_size (tuple[float, float], optional): Size of the figure. Defaults to (12, 6).
            linewidth (float, optional): Width of the line in the plot. Defaults to 0.7.
            color (str, optional): Color of the line in the plot. Defaults to 'blue'.
            grid_alpha (float, optional): Transparency of the grid lines. Defaults to 0.3.
            usetex (bool, optional): Use LaTeX for text rendering. Defaults to True.


        """

        if not has_matplotlib:
            print(
                "matplotlib is an optional dependency, pip install gana[all] to get optional dependencies"
            )
            return

        data = self(variable)

        def check_whats_changing():
            check_unique: dict[int, list] = {}
            for index in data['index']:
                for n, idx in enumerate(index):
                    if n not in check_unique:
                        check_unique[n] = []
                    if idx not in check_unique[n]:
                        check_unique[n].append(idx)
            _hold = []
            _free = []

            for unq in check_unique.values():
                if len(unq) == 1:
                    _hold.append(unq[0])
                else:
                    _free.append(unq)

            return _hold, _free

        hold, free = check_whats_changing()

        ax = plt.subplots(figsize=fig_size)[1]

        # the indices are the x-axis
        x = range(len(data['values']))
        # the values are the y-axis
        y = data["values"]

        if usetex:
            rc(
                'font',
                **{'family': 'serif', 'serif': ['Computer Modern'], 'size': font_size},
            )
            rc('text', usetex=usetex)
        else:
            rc('font', **{'size': font_size})

        if kind == 'line':
            ax.plot(x, y, linewidth=linewidth, color=color)

        elif kind == 'bar':
            ax.bar(x, y, linewidth=linewidth, color=color)

        title = rf'${variable.tag or variable.name}$'

        if len(hold) > 0:
            title += r' ('
            for h in hold:
                title += rf'{h}, '

            title = title[:-2] + r')'

        ax.set_title(title)
        ax.set_ylabel(r'Values')

        ax.set_xlabel(r'Indices')
        ax.grid(alpha=grid_alpha)

        if len(x) <= x_ticks_lim:
            ax.set_xticks(x)

            _xtick_labels = []
            for idx_latex, idx in zip(data['index_latex'], data['index']):
                for i in idx:
                    if i in hold:
                        idx_latex = idx_latex.replace(i + ",", '').replace(i, '')
                _xtick_labels.append(idx_latex)

            ax.set_xticklabels(_xtick_labels)

        plt.rcdefaults()

    def draw_line(self, **kwargs):
        """Alias for plot with kind='line'"""
        self.draw(kind='line', **kwargs)

    def draw_bar(self, **kwargs):
        """Alias for plot with kind='bar'"""
        self.draw(kind='bar', **kwargs)
