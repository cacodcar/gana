"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from math import prod

from ..elements.func import Func
from .constraint import C
from .ordered import Set
from .index import I
from ..elements.idx import Idx

if TYPE_CHECKING:
    from .parameter import P
    from .variable import V


class F(Set):
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
        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div
        self.one = one
        self.two = two

        if isinstance(one, list):
            if isinstance(two, list):
                raise ValueError('Cannot operate with two lists')
            index = (I(size=len(one)), two.index)

        elif isinstance(two, list):
            index = (one.index, I(size=len(two)))

        elif isinstance(one, (int, float)):
            if isinstance(two, (int, float)):
                raise ValueError('Cannot operate with two constants')
            index = (I(size=len(two)), two.index)

        elif isinstance(two, (int, float)):
            index = (one.index, I(size=len(one)))

        else:
            index = (one.index, two.index)

        lone = len(index[0])
        ltwo = len(index[1])

        if not lone % ltwo == 0 and not ltwo % lone == 0:
            raise ValueError('The indices are not compatible')

        # Handles the case when indices are mismatched

        if lone > ltwo:
            idxone = index[0]._
            idxtwo = index[1]._ * int(lone / ltwo)

        if ltwo > lone:
            idxone = index[0]._ * int(ltwo / lone)
            idxtwo = index[1]._

        if lone == ltwo:
            idxone = index[0]._
            idxtwo = index[1]._

        index = (I(*[idx for idx in zip(idxone, idxtwo)]),)

        super().__init__(*index)

        self.name = f'{one or ""}{self.rel}{two or ""}'

        if not self.index.name:
            self.index.name = rf'{index}'

        self._: list[Func] = []

        for idx, n in self.idx.items():
            if self.one is not None:
                if isinstance(self.one, list):
                    one_ = self.one[n]
                elif isinstance(self.one, (int, float)):
                    one_ = self.one
                else:
                    one_ = self.one(idx[0])
            else:
                one_ = None

            if self.two is not None:
                if isinstance(self.two, list):
                    two_ = self.two[n]
                elif isinstance(self.two, (int, float)):
                    two_ = self.two
                else:
                    two_ = self.two(idx[1])
            else:
                two_ = None

            if (self.add or self.sub) and two_ is None:
                self._.append(one_)
                continue

            if self.mul and (one_ is None or one_ in [0, 0.0]):
                self._.append(0)
                continue

            if not one_ and not two_:
                self._.append(0)
                continue

            self._.append(
                Func(
                    one=one_,
                    mul=self.mul,
                    add=self.add,
                    sub=self.sub,
                    div=self.div,
                    two=two_,
                    parent=self,
                    pos=n,
                )
            )

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

        if self.add:
            return rf'{one or ""} + {two or ""}'

        if self.sub:
            return rf'{one or ""} - {two or ""}'

        if self.mul:

            # handling special case where something is multiplied by -1
            if isinstance(one, (int, float)) and float(one) == -1.0:
                return rf'-{two or ""}'

            return rf'{str(one) or ""} \cdot {str(two) or ""}'

        if self.div:
            return rf'\frac{{{str(one) or ""}}}{{{str(two) or ""}}}'

    def pprint(self, descriptive: bool = False):
        """Display the function"""
        if descriptive:
            for f in self._:
                display(Math(f.latex()))
        else:
            display(Math(self.latex()))

    def isnnvar(self):
        """Is this a neg variable"""
        if (
            isinstance(self.one, (int, float))
            and self.one == 0
            and self.sub
            and not isinstance(self.two, F)
        ):
            return True

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
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self | P | V | int | float):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        else:
            return self + other

    def __sub__(self, other: Self | P | V):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return F(one=self, sub=True, two=other)

    def __rsub__(self, other: Self | P | V):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | P | V):
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                return 0
            if other in [1, 1.0]:
                return self

        if self.add:
            return F(one=other * self.one, add=True, two=other * self.two)

        if self.sub:
            return F(one=other * self.one, sub=True, two=other * self.two)

        return F(one=self, mul=True, two=other)

    def __truediv__(self, other: Self | P | V):
        if isinstance(other, (int, float)) and other in [1, 1.0]:
            return self

        if isinstance(other, (int, float)) and other in [0, 0.0]:
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

    def __call__(self, *key: tuple[Idx | I]) -> Func:
        if len(key) == 1 and isinstance(key[0], (int, Idx, I)):
            key = key[0]
        return self[self.idx[key]]

    def __getitem__(self, pos: int) -> Func:
        return self._[pos]

    def __iter__(self):
        for i in self._:
            yield i
