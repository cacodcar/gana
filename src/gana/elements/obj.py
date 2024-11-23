"""Objective Function"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from .x import X

if TYPE_CHECKING:
    from .func import Func
    from ..sets.function import F


class Obj(X):
    """Objective Function"""

    def __init__(self, func: Func):

        self.func = func

        super().__init__()

        for v in func.vars():
            v.features.append(self)

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
