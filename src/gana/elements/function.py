"""Function"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .constraint import Cons
from .element import X

if TYPE_CHECKING:
    from ..sets.functions import F
    from .variable import Var


class Func(X):
    """A function"""

    def __init__(
        self,
        rel: str,
        parent: F | Cons | Var = None,
        pos: int = None,
        one: float | Var | Self = None,
        two: float | Var | Self = None,
    ):

        pwr_one, pwr_two = 0, 0

        if one:
            # any parameter goes to two
            if isinstance(one, (float, int)):
                one_ = float(one)
                one = two
                two = one_
            else:
                pwr_one = one.pwr

        if two:
            if isinstance(two, (float, int)):
                two = float(two)
            else:
                pwr_two = two.pwr

        if rel == '×':
            self.pwr = pwr_one + pwr_two

        if rel == '+' or rel == '-':
            self.pwr = max(pwr_one, pwr_two)

        self.one = one
        self.two = two
        self.rel = rel

        super().__init__(parent=parent, pos=pos)

        # self.a = []  # variable vector
        # self.b = None  # parameter added or subtracted goes in the parameter vector
        self.struct = []

        self.name = f'{self.one or ""} {self.rel} {self.two or ""}'

    # we deal with the following forms of a function at the basic level
    # note that func can just be a var
    # I None +- func
    # II par +- func
    # III func +- par
    # IV func +- func
    # V par . func
    # VI func . par
    # VII func . func

    def elms(self):
        """Elements (Variables and Parameters) of the function"""
        return sum(
            [i.elms() if isinstance(i, Func) else [i] for i in [self.one, self.two]],
            [],
        )

    def rels(self):
        """Relations between variables"""
        rels = []
        if isinstance(self.one, Func):
            rels += self.one.rels()

        rels += [self.rel]

        if isinstance(self.two, Func):
            rels += self.two.rels()
        return rels

    @property
    def _(self):
        """The function as a list"""
        x = []
        for n, e in enumerate(self.elms()):
            if n > 0:
                x.append(self.rels()[n - 1])
            x.append(e)

        if x[0] is None:
            x = x[1:]
        else:
            x = ['+'] + x

        return x

    def b(self, zero: bool = False) -> int | float | None:
        """Parameter
        Args:
            zero (bool, optional): returns 0 instead of None. Defaults to False.
        """

        if isinstance(self._[-1], float):
            if self._[-2] == '+':
                return -self._[-1]
            if self._[-2] == '-':
                return self._[-1]
        if zero:
            return 0

    def a(self) -> list[float]:
        """Variable coefficient vector"""
        x = self._
        if isinstance(self._[-1], float) and self._[-2] in ['+', '-']:
            x = x[:-2]

        return x
        # a_ = []

        # for n, i in enumerate(x):
        #     if i == '+':
        #         a_.append(1.0)
        #     if i == '-':
        #         a_.append(-1.0)
        #     if i == '×':
        #         a_[n - 1] = a_[n - 1] * x[n + 1]

        # return a_

    def azzz(self) -> list[float | None]:
        """Matrix of variable coefficients"""

        if isinstance(self.one, Func):
            a += self.one.a()

        else:
            if self.rel == '+' or self.rel == '-':
                a.append(1.0)

            if self.rel == '×' and isinstance(self.two, float):
                a.append(self.two)

        if isinstance(self.two, Func):
            a += self.two.a()

        else:
            if self.rel == '+':
                a.append(1.0)

            if self.rel == '-':
                a.append(-1.0)

            if self.rel == '×' and isinstance(self.one, float):
                a.append(self.one)

    #     # if not self.one and not self.two:
    #     #     raise ValueError('Function must have at least one element')

    #     if self.one:

    #         if isinstance(self.one, (int, float)):
    #             self.one = float(self.one)

    #             if self.rel == '+':
    #                 self.b = -self.one

    #             if self.rel == '-':
    #                 self.b = -self.one

    #         elif isinstance(self.one, Func):
    #             self.a += self.one.a
    #             self.struct += self.one.struct

    #             if self.one.b:
    #                 if self.b:
    #                     self.b += self.one.b
    #                 else:
    #                     self.b = self.one.b

    #         else:
    #             # assumed to be a Var
    #             self.struct.append(self.one.n)

    #             if self.rel == '+' or self.rel == '-':
    #                 self.a.append(1.0)

    #             if self.rel == '×':
    #                 if isinstance(self.two, (int, float)):
    #                     self.a.append(self.two)

    #     else:
    #         if isinstance(self.two, (Func, int, float)) or self.rel == '×':
    #             raise ValueError('This operation is not possible')

    #     if self.two:

    #         if isinstance(self.two, (int, float)):

    #             if self.rel == '+':
    #                 self.b = -self.two

    #             if self.rel == '-':
    #                 self.b = self.two

    #         elif isinstance(self.two, Func):
    #             self.a += self.two.a
    #             self.struct += self.two.struct

    #             if self.two.b:
    #                 if self.b:
    #                     self.b += self.two.b
    #                 else:
    #                     self.b = self.two.b

    #         else:
    #             # assumed to be a Var
    #             self.struct.append(self.two.n)

    #             if self.rel == '+':

    #                 self.a.append(1.0)

    #             if self.rel == '-':
    #                 self.a.append(-1.0)

    #             if self.rel == '×':
    #                 if isinstance(self.one, (int, float)):
    #                     self.a.append(self.one)

    def latex(self) -> str:
        """Equation"""
        if self.one:
            if isinstance(self.one, (int, float)):
                one = self.one
            else:
                one = self.one.latex()
        else:
            one = ''

        if self.two:
            if isinstance(self.two, (int, float)):
                two = self.two

            else:
                two = self.two.latex()
        else:
            two = ''

        if self.rel == '+':
            return rf'{one} + {two}'

        if self.rel == '-':
            return rf'{one} - {two}'

        if self.rel == '×':
            return rf'{one} \cdot {two}'

        if self.rel == '÷':
            return rf'\frac{{{one}}}{{{two}}}'

    def matrix(self) -> list:
        """Variables in the function"""

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def __neg__(self):

        if self.one:
            one = self.one.__neg__()
        else:
            one = None

        if self.two:
            two = self.two

        else:
            two = None

        if self.rel == '+':

            rel = '-'

        elif self.rel == '-':

            rel = '+'
        else:
            rel = self.rel

        return Func(one=one, rel=rel, two=two)

    def __pos__(self):
        return self

    def __add__(self, other: float | Var | Self):
        # the number element is always taken at number two
        if isinstance(self.two, float):
            if isinstance(other, (int, float)):
                one = self.one
                two = self.two + float(other)
                if two < 0:
                    rel = '-'
                    two = -two
                else:
                    rel = '+'
            else:
                two = self.two
                one = self.one + other
                rel = '+'

            return Func(one=one, rel=rel, two=two)

        if isinstance(self.one, float):
            if isinstance(other, (int, float)):
                one = self.one + float(other)
                two = self.two
            else:
                one = self.one
                two = self.two + other

            return Func(one=one, rel='+', two=two)

        return Func(one=self, rel='+', two=other)

    def __radd__(self, other: float | Var | Self):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: float | Var | Self):

        if isinstance(self.two, float):
            if isinstance(other, (int, float)):
                one = self.one
                two = self.two - float(other)
                if two < 0:
                    rel = '-'
                    two = -two
                else:
                    rel = '+'
            else:
                one = self.one - other
                two = self.two
                rel = '-'

            return Func(one=one, rel=rel, two=two)

        if isinstance(self.one, float):
            if isinstance(other, (int, float)):
                one = self.one - float(other)
                two = self.two
            else:
                one = self.one
                two = self.two - other

            return Func(one=one, rel='-', two=two)

        return Func(one=self, rel='-', two=other)

    def __rsub__(self, other: float | Var | Self):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: float | Var | Self):
        return Func(one=self, two=other, rel='×')

    def __truediv__(self, other: float | Var | Self):
        return Func(one=self, two=other, rel='÷')

    def __eq__(self, other: float | Var | Self):
        return Cons(func=self - other)

    def __le__(self, other: float | Var | Self):
        return Cons(func=self - other, leq=True)

    def __ge__(self, other: float | Var | Self):
        return Cons(func=-self + other, leq=True)

    def __lt__(self, other: float | Var | Self):
        return self <= other

    def __gt__(self, other: float | Var | Self):
        return self >= other
