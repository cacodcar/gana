"""Basic operations"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .cons import Cons

if TYPE_CHECKING:
    from ..sets.function import F
    from .pvar import PVar
    from .var import Var


class Func:
    """A Mathematical Operation

    Operations are only betweeen two elements, one and two
    and have a rel betwen them, mul, add, sub, div

    elements can be a number (int, float), a variable (Var) or another operation (Func)

    In the base form of an Func haspar is True

    add (v + p)
    sub (v - p)
    mul (p*v)

    the placement of parameters (float, int) is consistent
    add/sub after the variable, mul before the variable

    Generally, if haspar is False operations can be:

    add (v1 + v2) or (opn + opn) or (v1 + opn) or (opn + v1)
    sub (v1 - v2) or (opn - opn) or (v1 - opn) or (opn - v1)
    mul (v1*v2) or (opn*opn) or (v1*opn) or (opn*v1)

    An Func cannot be defined but is rather generated when operating on:
    variables or constants or operations themselves
    """

    def __init__(
        self,
        one: float | Var | Self = 0,
        two: float | Var | Self = 0,
        mul: bool = False,
        add: bool = False,
        sub: bool = False,
        div: bool = False,
        parent: F | Cons | Var = None,
        pos: int = None,
    ):

        self.one = one
        self.two = two
        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        self.parent = parent
        self.pos = pos
        self.n = None

        if mul:
            self.rel = '×'
        elif add:
            self.rel = '+'
        elif sub:
            self.rel = '-'
        elif div:
            self.rel = '÷'

        self.name = f'{self.one or ""}{self.rel}{self.two or ""}'

    @property
    def variables(self) -> list[Var]:
        """Variables in the function"""
        return self.parent.variables[self.pos]

    @property
    def _(self):
        """Value of the function"""
        return self.eval()

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

    def eval(self, one: int | float = None, two: int | float = None):
        """Evaluate the function"""

        if one is None and self.one:
            if isinstance(self.one, Func):
                one_ = self.one.eval()
            elif isinstance(self.one, (int, float)):
                one_ = self.one
            else:
                one_ = self.one._
        else:
            one_ = one

        if two is None and self.two:
            if isinstance(self.two, Func):
                two_ = self.two.eval()
            elif isinstance(self.two, (int, float)):
                two_ = self.two
            else:
                two_ = self.two._
        else:
            two_ = two

        if self.mul:
            if not one_:
                one_ = 1
            if not two_:
                two_ = 1
            return one_ * two_
        if self.div:
            return one_ / two_
        if self.add:
            if not one_:
                one_ = 0
            if not two_:
                two_ = 0
            return one_ + two_
        if self.sub:
            if not one_:
                one_ = 0
            if not two_:
                two_ = 0
            return one_ - two_

    def latex(self) -> str:
        """Equation"""
        if self.one is not None:
            if isinstance(self.one, (int, float)):
                one = self.one
            else:
                one = self.one.latex()
        else:
            one = None

        if self.two is not None:
            if isinstance(self.two, (int, float)):
                two = self.two

            else:
                two = self.two.latex()
        else:
            two = None

        if two is None:
            return rf'{one}'

        if one is None:
            return rf'{two}'

        if self.add:
            return rf'{one} + {two}'

        if self.sub:
            if self.parent.funcs[0] and self.parent.funcs[1]:
                if not self.one.mul and not self.two.mul:
                    return rf'({one}) - ({two})'
            return rf'{one} - {two}'

        if self.mul:
            # handling negation case,
            if isinstance(one, (int, float)) and float(one) == -1.0:
                return rf'-{two}'
            return rf'{one} \cdot {two}'

        if self.div:
            return rf'\frac{{{one}}}{{{two}}}'

    def pprint(self):
        """Display the function"""
        display(Math(self.latex()))

    @property
    def isnegvar(self):
        """Is this a neg variable"""
        if (
            isinstance(self.one, (int, float))
            and self.one in [-1, -1.0]
            and self.mul
            and not isinstance(self.two, Func)
        ):
            return True

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
