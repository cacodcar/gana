"""A Paramter
"""

from __future__ import annotations

from math import prod
from typing import Self, TYPE_CHECKING
from sympy import IndexedBase, Symbol, symbols, Idx
from ..relational.f import F
from ..relational.c import C
from .m import M

if TYPE_CHECKING:
    from .s import S


class P:
    """A Parameter"""
    
    def __init__(self, *args: S, value: int | float | list | bool, name: str = 'Par'):
        self.index = args
        self.value = value
        self.name = name

        if isinstance(self.value, bool) and self.value is True:
            # Make big Ms
            self.value = M(big=True)

        if isinstance(self.value, list):
            if len(self) != len(self.value):
                raise ValueError(
                    f'Length of values ({len(self.value)}) must be equal to the size of the index set ({len(self)})'
                )

            # Make big Ms
            for i, v in enumerate(self.value):
                if isinstance(v, bool) and v is True:
                    self.value[i] = M(big=True)

    def x(self):
        """returns the value of the parameter"""
        return self.value

    @property
    def sym(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        if self.index:
            return IndexedBase(self.name)[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        else:
            return Symbol(self.name)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return prod([len(s) for s in self.index])

    def __neg__(self):

        return P(*self.index, value=[-i for i in self.value])

    def __pos__(self):
        return P(*self.index, value=[+i for i in self.value])

    def __abs__(self):
        return P(*self.index, value=[abs(i) for i in self.value])

    def __invert__(self):
        return P(*self.index, value=[~i for i in self.value])

    def __add__(self, other: Self):

        if isinstance(other, P):
            return P(
                *self.index, value=[i + j for i, j in zip(self.value, other.value)]
            )
        else:
            return F(one=self, two=other, rel='+')

    def __sub__(self, other: Self):
        if isinstance(other, P):
            return P(
                *self.index, value=[i - j for i, j in zip(self.value, other.value)]
            )
        else:
            return F(one=self, two=other, rel='-')

    def __mul__(self, other: Self):
        if isinstance(other, P):
            return P(
                *self.index, value=[i * j for i, j in zip(self.value, other.value)]
            )
        else:
            return F(one=self, two=other, rel='*')

    def __truediv__(self, other: Self):
        if isinstance(other, P):
            return P(
                *self.index, value=[i / j for i, j in zip(self.value, other.value)]
            )
        else:
            return F(one=self, two=other, rel='/')

    def __floordiv__(self, other: Self):

        return P(*self.index, value=[i // j for i, j in zip(self.value, other.value)])

    def __mod__(self, other: Self):

        return P(*self.index, value=[i % j for i, j in zip(self.value, other.value)])

    def __pow__(self, other: Self):

        return P(*self.index, value=[i**j for i, j in zip(self.value, other.value)])

    def __eq__(self, other: Self):

        if isinstance(other, P):
            check = list({i == j for i, j in zip(self.value, other.value)})
            print(check)
            if len(check) == 1 and check[0] is True:
                return True
            else:
                return False

        else:
            return C(lhs=self, rhs=other, rel='eq')

    def __le__(self, other: Self):

        if isinstance(other, P):
            check = [i <= j for i, j in zip(self.value, other.value)]
            if all(check):
                return True
            else:
                return False

        else:
            return C(lhs=self, rhs=other, rel='leq')

    def __ge__(self, other: Self):
        if isinstance(other, P):
            return not self <= other
        else:
            return C(lhs=self, rhs=other, rel='geq')

    def __lt__(self, other: Self):

        if isinstance(other, P):
            check = [i < j for i, j in zip(self.value, other.value)]
            if all(check):
                return True
            else:
                return False

        else:
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
            return not self < other
        else:
            return self >= other
