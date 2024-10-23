"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math

from ..elements.function import Func
from .constraints import C
from .ordered import ESet
from .indices import I

if TYPE_CHECKING:
    from sympy import Add

    from ..elements.index import Idx
    from .parameters import P
    from .variables import V


class F(ESet):
    """Provides some relational operation between Parameters and Variables"""

    def __init__(
        self,
        one: P | V | Self = 0,
        two: P | V | Self = 0,
        mul: bool = False,
        add: bool = False,
        sub: bool = False,
        div: bool = False,
    ):
        self._: list[Func] = []

        if mul:
            rel = '×'
        elif add:
            rel = '+'
        elif sub:
            rel = '-'
        elif div:
            rel = '÷'
        else:
            raise ValueError('one of mul, add, sub or div must be True')

        if isinstance(one, list):
            if isinstance(two, list):
                raise ValueError('Cannot operate with two lists')
            order = (I(size=len(one)), two.order)

        elif isinstance(two, list):
            order = (one.order, I(size=len(two)))

        elif isinstance(one, (int, float)):
            if isinstance(two, (int, float)):
                raise ValueError('Cannot operate with two constants')
            order = (one.order, I(size=len(two)))

        elif isinstance(two, (int, float)):
            order = (I(size=len(one)), two.order)

        else:
            order = (one.order, two.order)

        name = f'{one or ""}{rel}{two or ""}'

        super().__init__(*order, name=name)

        for n, idx in enumerate(self.idx()):

            one_, two_ = one, two
            if one and not isinstance(one, (int, float)):
                one_ = one(idx[0])

            if two and not isinstance(two, (int, float)):
                two_ = two(idx[1])

            self._.append(
                Func(
                    one=one_,
                    mul=mul,
                    add=add,
                    sub=sub,
                    div=div,
                    two=two_,
                    parent=self,
                    pos=n,
                )
            )

        self.one = one
        self.two = two
        self.rel = rel
        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        # the flag _fixed is changed when .fix(val) is called

        self.a, self.b = [], []

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
        one, two = None, None
        if self.one:
            one = self.one

        if self.two:
            two = self.two

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
