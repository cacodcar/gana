"""Objective Function"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from .element import X

if TYPE_CHECKING:
    from .function import Func


class Obj(X):
    """Objective Function"""

    def __init__(self, func: Func):

        self.func = func

        super().__init__()

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
