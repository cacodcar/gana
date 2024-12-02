"""Objective Function"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display


if TYPE_CHECKING:
    from .func import Func
    from ..sets.function import F


class Obj:
    """Objective Function"""

    def __init__(self, func: F):

        self.func: Func = func._[0]

        # number in the program
        self.n = None

        # name given by user in program
        self.pname: str = None

        for v in self.func.vars():
            v.features.append(self)

    @property
    def name(self):
        """name of the element"""
        return f'min({self.func})'

    def A(self) -> list[float | None]:
        """Parameter values"""
        return self.func.A()

    def X(self):
        """Variable positions"""
        return self.func.X()

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
