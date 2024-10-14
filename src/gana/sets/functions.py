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
        self.one = one
        self.two = two
        self.rel = rel

        if self.one:
            order = self.one.order

        elif self.two:
            order = self.two.order

        else:
            raise ValueError('one or two must be provided')

        super().__init__(*order)

        if self.one:
            self.name = f'{self.one}{self.rel}{self.two}'
        else:
            self.name = f'{self.rel}{self.two}'

        self._: list[Func] = []
        # the flag _fixed is changed when .fix(val) is called

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
        """Variables in the function"""

        return sum(
            [
                i.matrix() if isinstance(i, F) else [i.number]
                for i in [self.one, self.two]
                if i
            ],
            [],
        )

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

    def sympy(self) -> Add:
        """Equation"""
        # if self.rel == '+':
        #     if self.one:
        #         return self.one.sympy() + self.two.sympy()
        #     else:
        #         return self.two.sympy()

        # if self.rel == '-':
        #     if self.one:
        #         return self.one.sympy() - self.two.sympy()
        #     # this is used to generate negatives
        #     else:
        #         return -self.two.sympy()

        # if self.rel == '×':
        #     return self.one.sympy() * self.two.sympy()

        # if self.rel == '÷':
        #     return self.one.sympy() / self.two.sympy()

    def __neg__(self):
        if self.one:
            one = -self.one
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

    def __getitem__(self, *key: tuple[Idx] | Idx) -> Func:
        return self(*key)
