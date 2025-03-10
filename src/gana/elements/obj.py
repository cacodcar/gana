"""Objective Function"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display
from ..elements.var import Var

if TYPE_CHECKING:
    from ..sets.function import F
    from ..sets.variable import V
    from .func import Func


class Obj:
    """Objective Function"""

    def __init__(self, func: F | V):

        # self.idx = func.idx
        self.func: Var | Func = func._[0]

        self.funcs = func

        if isinstance(self.func, Var):
            self.func.features.append(self)
            self.isvar = True
            self.A = [1]
            self.X = [self.func.n]
        else:
            for v in self.func.variables:
                v.features.append(self)
            self.isvar = False
            self.A = self.func.A
            self.X = self.func.X

        # number in the program
        self.n = None

        # name given by user in program
        self.pname: str = None

    @property
    def name(self):
        """name of the element"""
        return f'min({self.func})'

    def sol(self, asfloat: bool = False):
        """Solution"""
        if asfloat:
            return self._
        display(Math(self.latex() + r'=' + rf'{self._}'))

    @property
    def _(self):
        """Objective as a list"""
        return self.func._

    def latex(self):
        """Latex representation"""
        return rf'min \hspace{{0.2cm}} {self.func.latex()}'

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def mps(self):
        """Name in MPS file"""
        return f'O{self.n}'

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
