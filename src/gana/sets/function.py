"""Function
"""

# A basic Function is of the type
# P*V, V + P, V - P
# P can be a number (int or float), parameter set (P) or list[int | float]
# for multiplication P comes before variable

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display


from ..elements.func import Func
from .constraint import C
from .index import I


if TYPE_CHECKING:
    from .parameter import P
    from .variable import V


class F:
    """Provides some relational operation between Parameters and Variables"""

    def __init__(
        self,
        one: int | float | list[int | float] | P | V | Self = 0,
        two: int | float | list[int | float] | P | V | Self = 0,
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

        if mul:
            self.rel = '×'
        elif add:
            self.rel = '+'
        elif sub:
            self.rel = '-'
        elif div:
            self.rel = '÷'
        else:
            raise ValueError('one of mul, add, sub or div must be True')

        # if the function is -1*v (negation)
        self.isnnvar = False

        self.consistent()

        # These are of the type P*V, V + P, V - P
        # indices should match in these cases
        from .parameter import P

        # if operating with V and a number
        if isinstance(self.one, (int, float)):
            one_ = self.one
            self.one = P(_=[self.one] * len(self.two))
            self.one.index = self.two.index
            self.one.name = str(one_)

        elif isinstance(self.two, (int, float)):
            two_ = self.two
            self.two = P(_=[self.two] * len(self.one))
            self.two.index = self.one.index
            self.two.name = str(two_)

        elif isinstance(self.one, list):
            self.one = P(I(size=len(self.one)), _=self.one)
            self.one.name = rf'Par{self.two.name.capitalize()}'

        elif isinstance(self.two, list):
            self.two = P(I(size=len(self.two)), _=self.two)
            self.two.name = rf'Par{self.one.name.capitalize()}'

        # At this point, both one and two are gana elements
        # P, V or F
        # There could be mismatches in the indices
        # Check for mismatched indices

        self.index = self.one.index + self.two.index

        self.name = f'{self.one or ""}{self.rel}{self.two or ""}'

        # order of declaration in the program
        self.n: int = None
        # name given by user in program
        self.pname: str = None

        self._: list[Func] = []

        mis = self.mismatch()

        if mis < 1:
            # two is longer
            one_ = [x for x in self.one._ for _ in range(-mis)]
            two_ = self.two._

        elif mis > 1:

            # one is longer
            one_ = self.one._
            two_ = [x for x in self.two._ for _ in range(mis)]

        else:

            # one and two are of the same length
            one_ = self.one._
            two_ = self.two._

        # one_ is None or 0 for negation
        if not one_:
            one_ = [None] * len(two_)

        for n, _ in enumerate(one_):

            self._.append(
                Func(
                    one=one_[n],
                    mul=self.mul,
                    add=self.add,
                    sub=self.sub,
                    div=self.div,
                    two=two_[n],
                    parent=self,
                    pos=n,
                )
            )

    def consistent(self):
        """Make function consistent"""
        from .parameter import P
        from .variable import V

        if isinstance(self.one, (int, float, list, P)) and isinstance(self.two, (V, F)):
            if self.add:
                # keep number after the variable/operation
                # additions are always v + p
                self.two, self.one = self.one, self.two
            if self.sub:
                # if negation, write as -1 * var
                if isinstance(self.one, int) and (self.one == 0 or not self.one):
                    self.one = -1
                    self.mul = True
                    self.sub = False
                    self.isnnvar = True

                else:
                    # keep number after the variable
                    # subtractions are always v - p
                    self.two, self.one = self.one, -self.two
                    self.sub = False
                    self.add = True

        if isinstance(self.two, (int, float, list, P)) and isinstance(self.one, (V, F)):
            if self.mul:
                # keep number before the variable/operation
                # multiplications are also p*v
                self.two, self.one = self.one, self.two

    def mismatch(self):
        """Determine mismatch between indices"""
        lone = len(self.one)
        ltwo = len(self.two)
        if not lone % ltwo == 0 and not ltwo % lone == 0:
            raise ValueError('The indices are not compatible')
        if lone > ltwo:
            return int(lone / ltwo)
        if ltwo > lone:
            # negative to indicate that two is greater than one
            return -int(ltwo / lone)
        return 1

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

        if self.mul:
            return F(one=other * self.one, mul=True, two=self.two)

        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self | P | V | int | float):
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                return 0
            if other in [1, 1.0]:
                return self
        return self * other

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

    # def __call__(self, *key: tuple[Idx | I]) -> Func:
    #     if len(key) == 1 and isinstance(key[0], (int, Idx, I)):
    #         key = key[0]
    #     return self[self.idx[key]]

    def __getitem__(self, pos: int) -> Func:
        return self._[pos]

    def __iter__(self):
        for i in self._:
            yield i

    def order(self) -> list:
        """order"""
        return len(self.index)

    def __len__(self):
        return len(self.index._)

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
