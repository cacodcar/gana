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
            # if there is a parameter in the end, that goes to the b matrix
            x = x[:-2]

        # here you get a list of tuples (rel, variable)
        x = list(zip(x[::2], x[1::2]))

        a_ = []

        for n, i in enumerate(x):
            if isinstance(i[1], float):
                # if multiplication by float
                if i[0] == '×':
                    a_[n - 1] = a_[n - 1] * i[1]
            else:
                if i[0] == '+':
                    a_.append(1.0)
                if i[0] == '-':
                    a_.append(-1.0)
        return a_

    def x(self) -> list[int]:
        """Structure of the function
        given as a list of number tags (n) for the variables (x)
        """
        x = self._
        if isinstance(self._[-1], float) and self._[-2] in ['+', '-']:
            x = x[:-2]
        x: list[Var] = x[1::2]
        return [i.n for i in x if not isinstance(i, float)]

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

    def matrix(self) -> tuple[list[float], int | float | None]:
        """Matrix representation"""
        return self.a(), self.b()

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
