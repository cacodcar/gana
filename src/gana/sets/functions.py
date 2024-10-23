"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

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
        self.one = one
        self.two = two
        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        if isinstance(one, list):
            if isinstance(two, list):
                raise ValueError('Cannot operate with two lists')
            order = (I(size=len(one)), two.order)

        elif isinstance(two, list):
            order = (one.order, I(size=len(two)))

        elif isinstance(one, (int, float)):
            if isinstance(two, (int, float)):
                raise ValueError('Cannot operate with two constants')
            order = (I(size=len(two)), two.order)

        elif isinstance(two, (int, float)):
            order = (one.order, I(size=len(one)))

        else:
            order = (one.order, two.order)

        name = f'{one or ""}{self.rel}{two or ""}'

        super().__init__(*order, name=name)

        for n, idx in enumerate(self.idx()):

            if one:
                if isinstance(one, list):
                    one_ = one[n]
                elif isinstance(one, (int, float)):
                    one_ = one
                else:
                    one_ = one(idx[0])
            else:
                one_ = None

            if two:
                if isinstance(two, list):
                    two_ = two[n]
                elif isinstance(two, (int, float)):
                    two_ = two
                else:
                    two_ = two(idx[1])
            else:
                two_ = None

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

        # the flag _fixed is changed when .fix(val) is called

        self.a, self.b = [], []

    @property
    def rel(self):
        """Relation between the two elements"""
        if self.mul:
            return '×'
        elif self.add:
            return '+'
        elif self.sub:
            return '-'
        elif self.div:
            return '÷'
        else:
            raise ValueError('one of mul, add, sub or div must be True')

    def matrix(self):
        """Variable and Parameter Vectors"""

    def par(self):
        """Parameters in the function"""

    def latex(self) -> str:
        """Equation"""
        if self.one:
            if isinstance(self.one, (int, float)):
                one = self.one
            else:
                one = self.one.latex()
        else:
            one = None

        if self.two:
            if isinstance(self.two, (int, float)):
                two = self.two
            else:
                two = self.two.latex()
        else:
            two = None

        if self.add:
            return rf'{one or ""} + {two or ""}'

        if self.sub:
            return rf'{one or ""} - {two or ""}'

        if self.mul:
            return rf'{one or ""} \cdot {two or ""}'

        if self.div:
            return rf'\frac{{{one or ""}}}{{{two or ""}}}'

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def __neg__(self):

        if self.add:
            return F(one=-self.one, sub=True, two=self.two)

        if self.sub:
            return F(one=-self.one, add=True, two=self.two)

        if self.mul:
            return F(one=-self.one, mul=True, two=self.two)

        if self.div:
            return F(one=-self.one, div=True, two=self.two)

    def __pos__(self):
        return self

    def __add__(self, other: Self | P | V):
        if isinstance(other, int) and other == 0:
            return self
        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self | P | V | int):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: Self | P | V):
        if other == 0:
            return self
        return F(one=self, sub=True, two=other)

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
        return F(one=self, mul=True, two=other)

    def __truediv__(self, other: Self | P | V):
        if other == 1:
            return self

        if isinstance(other, int) and other == 0:
            return self
        return F(one=self, div=True, two=other)

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
