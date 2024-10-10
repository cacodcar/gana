"""Constraint"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING
from IPython.display import Math, display

from .element import X

if TYPE_CHECKING:
    from .variable import Var
    from .function import Func
    from ..sets.constraints import C


class Cons(X):
    """A constraint"""

    def __init__(
        self,
        func: Func | Var | float,
        leq: bool = False,
        pos: int = None,
        parent: C = None,
    ):
        self.func = func
        self.leq = leq

        super().__init__(parent=parent, pos=pos)

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'{self.func.latex()} {rel} 0'

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))
