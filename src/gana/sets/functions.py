"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math

from .constraints import C
from .ordered import Set
from ..elements.function import Func


if TYPE_CHECKING:
    from sympy import Add

    from .parameters import P
    from .variables import V
    from ..elements.index import Idx
    from .indices import I


class F(Set):
    """Provides some relational operation between Parameters and Variables"""

    def __init__(
        self,
        one: P | V | Self = None,
        rel: str = '+',
        two: P | V | Self = None,
    ):
        self.one: P | V | Self = one
        self.two = two
        self.rel = rel

        if self.one:
            order = self.one.order
        elif self.two:
            order = self.two.order

        super().__init__(*order)

        if self.one:
            self.name = f'{self.one}{self.rel}{self.two}'
        else:
            self.name = f'{self.rel}{self.two}'

        self._: list[Func] = []
        # the flag _fixed is changed when .fix(val) is called

    def process(self):

        if self.one and len(self.one) != len(self.two):
            raise ValueError(
                'Cannot operate with variable sets with different cardinalities'
            )
        if self.one:
            self._ = [
                Func(
                    parent=self,
                    pos=n,
                    one=self.one(idx),
                    rel=self.rel,
                    two=self.two(idx),
                )
                for n, idx in enumerate(self.idx())
            ]
        else:
            self._ = [
                Func(
                    parent=self,
                    pos=n,
                    rel=self.rel,
                    two=self.two(idx),
                )
                for n, idx in enumerate(self.idx())
            ]

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
        if self.rel == '+':
            if self.one:
                return self.one.sympy() + self.two.sympy()
            else:
                return self.two.sympy()

        if self.rel == '-':
            if self.one:
                return self.one.sympy() - self.two.sympy()
            # this is used to generate negatives
            else:
                return -self.two.sympy()

        if self.rel == '×':
            return self.one.sympy() * self.two.sympy()

        if self.rel == '÷':
            return self.one.sympy() / self.two.sympy()

    def __neg__(self):

        self._ = [-i for i in self._]
        return self

    def __pos__(self):
        return self

    def __add__(self, other: Self | P | V):
        self._ = [a + b for a, b in zip(self._, other._)]
        return self

    def __radd__(self, other: Self | P | V | int):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: Self | P | V):
        self._ = [a - b for a, b in zip(self._, other._)]
        return self

    def __rsub__(self, other: Self | P | V):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | P | V):
        self._ = [a * b for a, b in zip(self._, other._)]
        return self

    def __truediv__(self, other: Self | P | V):
        self._ = [a / b for a, b in zip(self._, other._)]
        return self

    def __eq__(self, other: Self | P | V):
        return C(lhs=self, rel='eq', rhs=other)

    def __le__(self, other: Self | P | V):
        return C(lhs=self, rel='le', rhs=other)

    def __ge__(self, other: Self | P | V):
        return C(lhs=self, rel='ge', rhs=other)

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
