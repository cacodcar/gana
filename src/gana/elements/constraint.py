"""Constraint"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from IPython.display import Math, display

from .element import X

if TYPE_CHECKING:
    from ..sets.constraints import C
    from .function import Func
    from .variable import Var


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

    @property
    def _(self):
        """Constraint as a list"""
        return self.func._

    def b(self, zero: bool = False) -> int | float | None:
        """RHS parameter"""
        return self.func.b(zero)

    def a(self) -> list[float | None]:
        """The variable vector"""
        return self.func.a()

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
