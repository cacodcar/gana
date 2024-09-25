"""A Paramter
"""

from __future__ import annotations

from itertools import product
from math import prod
from typing import TYPE_CHECKING, Self

from sympy import Idx, IndexedBase, Symbol, symbols

from ..relational.c import C
from ..relational.f import F
from .m import M
from .v import V
from .z import Z

if TYPE_CHECKING:
    from .s import S


class P:
    """A Parameter"""

    def __init__(self, *args: S, _: int | float | list | bool = 0, name: str = 'Param'):
        self.index = args
        self._ = _
        self.name = name
        # keeps a count of, updated in program
        self.count: int = None

        if isinstance(self._, bool) and self._ is True:
            # True instances big Ms
            self._ = M()

        if isinstance(self._, (int, float)):
            if self.index:
                # if a scalar value is passed to a parameter with multiple indices
                # it is converted to a list of the same repeated value
                self._ = [self._] * len(self)

        if isinstance(self._, list):
            if self.index and len(self) != len(self._):
                raise ValueError(
                    f'Length of values ({len(self._)}) must be equal to the size of the index set ({len(self)})'
                )

            # Make big Ms in list
            for i, v in enumerate(self._):
                if isinstance(v, bool) and v is True:
                    self._[i] = M()

        if self.index:
            # values are attached to indices in a dictionary
            # this helps access for getitem etc
            self._ = {
                idx: self._[n]
                for n, idx in enumerate(list(product(*[s.members for s in self.index])))
            }

        else:
            # if list, just give positions as indices
            if isinstance(self._, list):
                self._ = {n: v for n, v in enumerate(self._)}
            # if single value (float), give it a zero index
            else:
                self._ = {0: self._}

    @property
    def sym(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        if self.name:
            if self.index:
                return (
                    IndexedBase(self.name)[
                        symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
                    ]
                    if isinstance(self._, dict)
                    else self._
                )
            else:
                return Symbol(self.name) if isinstance(self._, dict) else self._
        else:
            return Symbol('') if isinstance(self._, dict) else self._

    @property
    def idx(self) -> list[tuple]:
        """index"""
        return list(
            product(*[s.members if isinstance(s, S) else [s] for s in self.index])
        )

    @staticmethod
    def _bigm():
        return M()

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return prod([len(s) for s in self.index])

    def __getitem__(self, key: int | tuple):
        return self._[key]

    def __neg__(self):

        return P(*self.index, _=[-i for i in self._])

    def __pos__(self):
        return P(*self.index, _=[+i for i in self._])

    def __abs__(self):
        return P(*self.index, _=[abs(i) for i in self._])

    def __invert__(self):
        return P(*self.index, _=[~i for i in self._])

    # the ones below do this:
    # compare themselves to big Ms, Parameters, Variables, and Functions
    def __add__(self, other: Self):

        if isinstance(other, M):
            # big M is always bigger than any number
            return M()

        if isinstance(other, Z):
            # zero, like me, has no real impact
            return self

        if isinstance(other, P):
            # to handle big M values in list
            # I could manage M + int | float = M
            # not int | float + M = M
            return P(
                *self.index,
                _=[
                    i + j if not isinstance(i, M) else M()
                    for i, j in zip(self._, other._)
                ],
            )

        if isinstance(other, V):
            if self._ and other._:
                # evaluated variables return Parameters
                return P(
                    *self.index,
                    _=[
                        i + j if not isinstance(i, M) else M()
                        for i, j in zip(self._, other._)
                    ],
                )

            else:
                # unevaluated variables return function
                return F(one=self, rel='+', two=other)

        if isinstance(other, F):
            # added to a function returns a function
            return F(one=self, two=other, rel='+')

    def __sub__(self, other: Self):

        if isinstance(other, M):
            return M()

        if isinstance(other, P):
            return P(
                *self.index,
                _=[
                    i - j if not isinstance(i, M) else M()
                    for i, j in zip(self._, other._)
                ],
            )
        if isinstance(other, F):
            return F(one=self, two=other, rel='-')

        if isinstance(other, V):
            if self._ and other._:
                return P(
                    *self.index,
                    _=[
                        i - j if not isinstance(i, M) else M()
                        for i, j in zip(self._, other._)
                    ],
                )
            else:
                return F(one=self, rel='-', two=other)

    def __mul__(self, other: Self):
        if isinstance(other, P):
            return P(
                *self.index,
                _=[
                    i * j if not isinstance(i, M) else M()
                    for i, j in zip(self._, other._)
                ],
            )

        if isinstance(other, F):
            return F(one=self, rel='*', two=other)

        if isinstance(other, V):
            if self._ and other._:
                return P(
                    *self.index,
                    _=[
                        i * j if not isinstance(i, M) else M()
                        for i, j in zip(self._, other._)
                    ],
                )
            else:
                return F(one=self, rel='*', two=other)

    def __truediv__(self, other: Self):
        if isinstance(other, P):
            return P(*self.index, _=[i / j for i, j in zip(self._, other._)])
        if isinstance(other, F):
            return F(one=self, two=other, rel='/')
        if isinstance(other, V):
            if self._ and other._:
                return P(*self.index, _=[i / j for i, j in zip(self._, other._)])
            else:
                return F(one=self, rel='/', two=other)

    def __floordiv__(self, other: Self):

        return P(*self.index, _=[i // j for i, j in zip(self._, other._)])

    def __mod__(self, other: Self):

        return P(*self.index, _=[i % j for i, j in zip(self._, other._)])

    def __pow__(self, other: Self):

        return P(*self.index, _=[i**j for i, j in zip(self._, other._)])

    def __eq__(self, other: Self):

        if isinstance(other, P):
            check = list({i == j for i, j in zip(self._, other._)})
            if len(check) == 1 and check[0] is True:
                return True
            else:
                return False

        else:
            return C(lhs=self, rhs=other, rel='eq')

    def __le__(self, other: Self):

        if isinstance(other, P):
            check = [i <= j for i, j in zip(self._, other._)]
            if all(check):
                return True
            else:
                return False

        else:
            return C(lhs=self, rhs=other, rel='le')

    def __ge__(self, other: Self):
        if isinstance(other, P):
            return not self <= other
        else:
            return C(lhs=self, rhs=other, rel='ge')

    def __lt__(self, other: Self):

        if isinstance(other, P):
            check = [i < j for i, j in zip(self._, other._)]
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
