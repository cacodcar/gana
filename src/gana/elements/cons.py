"""Constraint"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

if TYPE_CHECKING:
    from ..sets.constraint import C
    from .func import Func


class Cons:
    """A constraint"""

    def __init__(
        self,
        func: Func,
        leq: bool = False,
        pos: int = None,
        parent: C = None,
        nn: bool = False,
    ):

        self.parent = parent
        self.pos = pos
        self.func = func

        self.nn = nn
        self.n = None

        if leq:
            self.name = self.func.name + r'<=0'
        else:
            self.name = self.func.name + r'=0'

        self.leq = leq

        for v in func.variables:
            if not self.nn and v:
                v.features.append(self)

    @property
    def A(self) -> list[float | None]:
        """Variable Coefficients"""
        return self.parent.A[self.pos]

    @property
    def X(self) -> list[None | int]:
        """Variables"""
        return self.parent.X[self.pos]

    @property
    def B(self) -> float | None:
        """Constant"""
        return self.parent.B[self.pos]

    @property
    def F(self) -> float | None:
        """Theta coefficiencts"""
        return self.parent.F[self.pos]

    @property
    def Z(self) -> float | None:
        """Thetas"""
        return self.parent.Z[self.pos]

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
    def struct(self):
        """Constraint elements as a list"""
        return self.func.struct

    @property
    def _(self):
        """Value of the lhs"""
        return self.func._

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

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
