"""A Paramter
"""

from __future__ import annotations

from math import prod
from typing import Self, TYPE_CHECKING

from IPython.display import Math
from sympy import Idx, IndexedBase, Symbol, symbols

from .constraints import C
from .functions import F
from .variables import V
from ..value.bigm import M

from .ordered import Set

if TYPE_CHECKING:
    from .indices import I
    from ..elements.index import Idx


class P(Set):
    """A Parameter"""

    def __init__(
        self, *indices: Idx | I, _: list[int | float | bool], name: str = 'Param'
    ):

        super().__init__(*indices)

        self._: list[float | M] = _

    def process(self):
        # Make big Ms in list

        if len(self) != len(self._):
            raise ValueError(
                f'Length of values ({len(self._)}) must be equal to the size of the index set ({len(self)})'
            )

        for n, p in enumerate(self._):
            if isinstance(p, bool) and p is True:
                self._[n] = M()
            # convert any into float
            self._[n] = float(p)

        self.name = self.name.capitalize()

    def latex(self) -> str:
        """LaTeX representation"""
        return str(self) + r'_{' + ', '.join(rf'{m}' for m in self.index) + r'}'

    def matrix(self):
        """Matrix Representation"""

    def pprint(self) -> Math:
        """Display the variables"""
        return Math(self.latex())

    def sympy(self) -> IndexedBase | Symbol:
        """symbolic representation"""

        return IndexedBase(str(self))[
            symbols(",".join([f'{d}' for d in self.order]), cls=Idx)
        ]

    def __neg__(self):
        return P(*self.order, _=[-i for i in self._])
        # if isinstance(self._, list):
        #     return P(*self.index, _=[-i for i in self._])
        # else:
        #     return P(*self.index, _=-self._)

    def __pos__(self):
        return self

    def __abs__(self):
        return P(*self.order, _=[abs(i) for i in self._])

    # --- Handling basic operations----
    # if there is a zero on the left, just return P
    # if the other is a parameter, add the values
    # if the other is a function/variable, return a function

    # r<operation>
    # for the right hand side operations
    # they only kick in when the left hand side operator
    # does not have the operation/the operation did not work
    # in this case, we just do the equivalent self
    def __add__(self, other: Self):

        if other == 0:
            return self

        if isinstance(other, P):
            print([i + j for i, j in zip(self._, other._)])
            self._ = [i._[0] + j._[0] for i, j in zip(self._, other._)]

        return F(one=self, rel='+', two=other)

    def __radd__(self, other: Self):
        return self + other

    def __sub__(self, other: Self):
        if other == 0:
            return self
        if isinstance(other, P):
            self._ = [i - j for i, j in zip(self._, other._)]
            return self
        return F(one=self, rel='-', two=other)

    def __rsub__(self, other: Self):
        return self - other

    def __mul__(self, other: Self):
        if isinstance(other, P):
            self._ = [i * j for i, j in zip(self._, other._)]
            return self
        return F(one=self, rel='×', two=other)

    def __rmul__(self, other: Self):
        if other == 1:
            return self
        return self * other

    def __truediv__(self, other: Self):
        if isinstance(other, P):
            return P(*self.index, _=[i / j for i, j in zip(self._, other._)])
        if isinstance(other, F):
            return F(one=self, two=other, rel='÷')
        if isinstance(other, V):
            return F(one=self, rel='÷', two=other)

    def __rtruediv__(self, other: Self):
        return other * self

    def __floordiv__(self, other: Self):

        return P(*self.index, _=[i // j for i, j in zip(self._, other._)])

    def __mod__(self, other: Self):

        return P(*self.index, _=[i % j for i, j in zip(self._, other._)])

    def __pow__(self, other: Self):

        return P(*self.index, _=[i**j for i, j in zip(self._, other._)])

    def __eq__(self, other: Self):

        if isinstance(other, P):
            return all([i == j for i, j in zip(self._, other._)])
        return C(lhs=self, rhs=other, rel='eq')

    def __le__(self, other: Self):

        if isinstance(other, P):
            return all([i <= j for i, j in zip(self._, other._)])
        return C(lhs=self, rhs=other, rel='le')

    def __ge__(self, other: Self):
        if isinstance(other, P):
            return all([i >= j for i, j in zip(self._, other._)])
        return C(lhs=self, rhs=other, rel='ge')

    def __lt__(self, other: Self):

        if isinstance(other, P):
            return all([i < j for i, j in zip(self._, other._)])
        return self <= other

    def __ne__(self, other: Self):
        if isinstance(other, P):
            return not self == other
        else:
            raise TypeError(
                f"unsupported operand type(s) for !=: 'P' and '{type(other)}'"
            )

    def __gt__(self, other: Self):
        if isinstance(other, P):
            return all([i > j for i, j in zip(self._, other._)])
        return self >= other

    def __iter__(self):
        for i in self._:
            yield i

    def __call__(self, *key: tuple[Idx] | Idx) -> Self:
        if len(key) == 1:
            return self._[self.idx().index(key[0])]
        return self._[self.idx().index(key)]

    def __getitem__(self, *key: tuple[Idx]):
        return self(*key)
