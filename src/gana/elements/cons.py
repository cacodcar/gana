"""Constraint"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from .x import X

if TYPE_CHECKING:
    from ..sets.constraint import C
    from .func import Func
    from .var import Var


class Cons(X):
    """A constraint"""

    def __init__(
        self,
        func: Func | Var,
        leq: bool = False,
        pos: int = None,
        parent: C = None,
    ):

        super().__init__(parent=parent, pos=pos)

        self.func = func

        if leq:
            self.name = self.func.name + r'<=0'
        else:
            self.name = self.func.name + r'=0'

        self.leq = leq

        for v in func.vars():
            if not self.nn and v:
                v.features.append(self)

    @property
    def nn(self):
        """Non-negativity Constraint"""
        if self.func.isnnvar() and self.leq:
            return True

    @property
    def eq(self):
        """Equality Constraint"""
        return not self.leq

    @property
    def one(self):
        """element one in function"""
        return self.func.one

    @property
    def two(self):
        """element two in function"""
        return self.func.two

    @property
    def elms(self):
        """Constraint elements as a list"""
        return self.func.elms

    @property
    def _(self):
        """Value of the lhs"""
        return self.func._

    def B(self, zero: bool = True) -> int | float | None:
        """RHS parameter"""
        return self.func.B(zero)

    def A(self) -> list[float]:
        """The variable vector"""
        return self.func.A()

    def X(self) -> list[int]:
        """The structure of the constraint
        given as a list of the number tags of variables
        """
        return self.func.X()

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'{self.func.latex()} {rel} 0'

    def sol(self):
        """Solution"""
        if self.leq:
            display(Math(self.func.latex() + r'=' + rf'{self._}'))

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def mps(self):
        """Name in MPS file"""
        return f'C{self.n}'
