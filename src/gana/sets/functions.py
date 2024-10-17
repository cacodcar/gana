"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math

from ..elements.function import Func
from .constraints import C
from .ordered import Set

if TYPE_CHECKING:
    from sympy import Add

    from ..elements.index import Idx
    from .indices import I
    from .parameters import P
    from .variables import V


class F(Set):
    """Provides some relational operation between Parameters and Variables"""

    def __init__(
        self,
        one: P | V | Self = None,
        rel: str = '+',
        two: P | V | Self = None,
    ):
        ord_one, ord_two = None, None
        if one:
            if not isinstance(one, (int, float)):
                ord_one = one.order
            else:
                one = float(one)
                ord_one = two.order

        if two:
            if not isinstance(two, (int, float)):
                ord_two = two.order
            else:
                two = float(two)
                ord_two = one.order

        if not two and not one:
            raise ValueError('one or two must be provided')

        if ord_one and ord_two:
            order = max(ord_one, ord_two)
        elif ord_one and not ord_two:
            order = ord_one
        elif not ord_one and ord_two:
            order = ord_two
        else:
            raise ValueError('Cannot operate with two constants')

        self.one = one
        self.two = two
        self.rel = rel

        super().__init__(*order)

        self.name = f'{self.one or ""}{self.rel}{self.two or ""}'

        self._: list[Func] = []
        # the flag _fixed is changed when .fix(val) is called

        self.a, self.b = [], []

    def process(self):

        if (
            self.one
            and not isinstance(self.one, (float, int))
            and not isinstance(self.two, (float, int))
            and len(self.one) != len(self.two)
        ):
            raise ValueError(
                'Cannot operate with variable sets with different cardinalities'
            )

        for n, idx in enumerate(self.idx()):
            if self.one:
                if isinstance(self.one, (int, float)):
                    one = self.one
                else:
                    one = self.one(idx)
            else:
                one = None

            if self.two:
                if isinstance(self.two, (int, float)):
                    two = self.two
                else:
                    two = self.two(idx)

            else:
                two = None

            self._.append(Func(parent=self, pos=n, one=one, rel=self.rel, two=two))

    def matrix(self):
        """Variable and Parameter Vectors"""

    def par(self):
        """Parameters in the function"""

    def latex(self) -> str:
        """Equation"""
        if self.rel == '+':
            if self.one:
                return rf'{self.one.latex()} + {self.two.latex()}'
            else:
                return rf'{self.two.latex()}'

        if self.rel == '-':
            if self.one:
                return rf'{self.one.latex()} - {self.two.latex()}'
            # this is used to generate negatives
            else:
                return rf'-{self.two.latex()}'

        if self.rel == '×':
            return rf'{self.one.latex()} \cdot {self.two.latex()}'

        if self.rel == '÷':
            return rf'\frac{{{self.one.latex()}}}{{{self.two.latex()}}}'

    def pprint(self) -> Math:
        """Display the function"""
        Math(self.latex())

    def __neg__(self):
        if self.one:
            one = self.one
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

        f = F(one=one, rel=rel, two=two)
        f._ = [-i for i in self._]
        return f

    def __pos__(self):
        return self

    def __add__(self, other: Self | P | V):

        if other == 0:
            return self

        if isinstance(other, int) and other == 0:
            return self
        f = F(one=self, rel='+', two=other)
        f._ = [a + b for a, b in zip(self._, other._)]
        return f

    def __radd__(self, other: Self | P | V | int):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: Self | P | V):
        if other == 0:
            return self

        f = F(one=self, rel='-', two=other)
        f._ = [a - b for a, b in zip(self._, other._)]
        return f

    def __rsub__(self, other: Self | P | V):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | P | V):
        if other == 1:
            return self

        if isinstance(other, int) and other == 0:
            return self
        f = F(one=self, rel='×', two=other)
        f._ = [a * b for a, b in zip(self._, other._)]
        return f

    def __truediv__(self, other: Self | P | V):
        if other == 1:
            return self

        if isinstance(other, int) and other == 0:
            return self
        f = F(one=self, rel='÷', two=other)
        f._ = [a / b for a, b in zip(self._, other._)]
        return f

    def __eq__(self, other: Self | P | V):
        return C(funcs=self - other)

    def __le__(self, other: Self | P | V):
        return C(funcs=self - other, leq=True)

    def __ge__(self, other: Self | P | V):
        return C(funcs=-self + other, leq=True)

    def __lt__(self, other: Self | P | V):
        return self <= other

    def __gt__(self, other: Self | P | V):
        return self >= other

    def __call__(self, *key: tuple[Idx] | Idx) -> Func:
        if len(key) == 1:
            return self._[self.idx().index(key[0])]
        return self._[self.idx().index(key)]

    def __getitem__(self, pos: int) -> Func:
        return self._[pos]
