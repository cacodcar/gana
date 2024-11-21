"""Variable"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .constraint import Cons
from .element import X

from ..elements.function import Func

if TYPE_CHECKING:
    from ..sets.variable import V


class Var(X):
    """A variable"""

    def __init__(
        self,
        parent: V,
        pos: int,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
    ):

        # if the variable is an integer variable
        self.itg = itg
        # if the variable is binary
        self.bnr = bnr
        # if the variable is non negative
        self.nn = nn

        # the value taken by the variable
        self._ = None

        super().__init__(parent=parent, pos=pos)

        # in what constraints the variable appears
        self.features: list[Cons] = []

    def latex(self):
        """Latex representation"""

        name, sup = self.parent.nsplit()
        return (
            name
            + sup
            + r'_{'
            + rf'{self.parent.index[self.pos]}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def sol(self):
        """Solution"""
        display(Math(self.latex() + r'=' + rf'{self._}'))

    def mps(self):
        """Name in MPS file"""
        if self.bnr:
            return f'X{self.n}'
        return f'V{self.n}'

    def vars(self):
        """Self"""
        return [self]

    def isnnvar(self):
        """Is nnvar"""
        return self.nn

    def isfix(self):
        """Is fixed"""
        if self._:
            return True

    def __pos__(self):
        return Func(add=True, two=self)

    def __neg__(self):
        return Func(sub=True, two=self)

    def __add__(self, other: Self | Func):
        # useful for the case of 0 + x
        # comes up when using sum()
        if other is None:
            return self
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return Func(one=self, add=True, two=other)

    def __radd__(self, other: Self | Func):
        if other is None:
            return self
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                return self
            other = float(other)
        return self + other

    def __sub__(self, other: Self | Func):
        if other is None:
            return self
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return Func(one=self, sub=True, two=other)

    def __rsub__(self, other: Self | Func | int):
        if other is None:
            return -self
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                return -self
            other = float(other)
        return -self + other

    def __mul__(self, other: Self | Func):
        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                return self
            if other in [0, 0.0]:
                return 0
        return Func(one=self, mul=True, two=other)

    def __rmul__(self, other: Self | Func | int):
        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                return self
            if other in [0, 0.0]:
                return 0
        return Func(one=other, mul=True, two=self)

    def __truediv__(self, other: Self | Func):
        return Func(one=self, div=True, two=other)

    def __rtruediv__(self, other: Self | Func | int):

        if isinstance(other, (int, float)) and other in [1, 1.0]:
            return self
        else:
            return Func(one=other, div=True, two=self)

    def __eq__(self, other):
        return Cons(func=self - other)

    def __le__(self, other):
        return Cons(func=self - other, leq=True)

    def __ge__(self, other):
        return Cons(func=other - self, leq=True)

    def __lt__(self, other):

        return self <= other

    def __gt__(self, other):

        return self >= other

    def __pow__(self, other: int):
        f = self
        for _ in range(other - 1):
            f *= self
        return f
