"""A Paramter
"""

from itertools import product
from math import prod
from typing import Self

from IPython.display import Math
from sympy import Idx, IndexedBase, Symbol, symbols

from .constraint import C
from .function import F
from ..value.bigm import M
from ..value.zero import Z
from .index import I
from .variable import V


class P:
    """A Parameter"""

    def __init__(self, *index: I, _: int | float | list | bool, name: str = 'Param'):
        if index:
            self.index = index
            # This works well for variables generated at the indices
            # of a variable set
        else:
            self.index = I(0, name=f'{name}')

        self.name = name
        self._: list[Self] = _
        # keeps a count of, updated in program
        self.count: int = None

        # if a parameter is declared as a child (at an constituent index)
        # the mum is the parent parameter
        self.mum = None

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

    def idx(self) -> list[tuple]:
        """index"""
        if not self.mum:
            return list(
                product(*[s._ if isinstance(s, I) else [s] for s in self.index])
            )
        else:
            return self.index

    def latex(self) -> str:
        """LaTeX representation"""
        return str(self) + r'_{' + ', '.join(rf'{m}' for m in self.index) + r'}'

    def sympy(self) -> IndexedBase | Symbol:
        """symbolic representation"""

        if isinstance(self._, list):
            if len(self._) == 1:
                if isinstance(self._[0], P):
                    return self._[0]._[0]

                else:
                    return self._[0]

            else:
                if self.index:
                    return IndexedBase(str(self))[
                        symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
                    ]
                else:
                    return Symbol(str(self))
        else:
            if isinstance(self._, P):
                return self._._

            else:
                return self._

    def __str__(self):
        return rf'{self.name}'.capitalize()

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return prod([len(s) if isinstance(s, I) else 1 for s in self.index])

    def __getitem__(self, key: int | tuple):

        if isinstance(key, tuple):
            return self._[self.idx().index(key)]

        if isinstance(key, int):
            return self._[key]

    def __neg__(self):
        if isinstance(self._, list):
            return P(*self.index, _=[-i for i in self._])
        else:
            return P(*self.index, _=-self._)

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
                _=[i + j for i, j in zip(self._, other._)],
            )

        if isinstance(other, V):
            if self._ and other._:
                # evaluated variables return Parameters
                return P(
                    *self.index,
                    _=[i + j for i, j in zip(self._, other._)],
                )

            else:
                # unevaluated variables return function
                return F(one=self, rel='+', two=other)

        if isinstance(other, F):
            # added to a function returns a function
            return F(one=self, two=other, rel='+')

    def __radd__(self, other: Self):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: Self):

        if isinstance(other, M):
            return M()

        if isinstance(other, P):
            return P(
                *self.index,
                _=[i - j for i, j in zip(self._, other._)],
            )
        if isinstance(other, F):
            return F(one=self, two=other, rel='-')

        if isinstance(other, V):
            if self._ and other._:
                return P(
                    *self.index,
                    _=[i - j for i, j in zip(self._, other._)],
                )
            else:
                return F(one=self, rel='-', two=other)

    def __rsub__(self, other: Self):
        return self - other

    def __mul__(self, other: Self):
        if isinstance(other, P):
            return P(
                *self.index,
                _=[i * j for i, j in zip(self._, other._)],
            )

        if isinstance(other, F):
            return F(one=self, rel='×', two=other)

        if isinstance(other, V):
            return F(one=self, rel='×', two=other)

    def __rmul__(self, other: Self):
        return other * self

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
            if isinstance(self._, list) and all(
                [i == j for i, j in zip(self._, other._)]
            ):
                return True
            elif isinstance(self._, (int, float)) and self._ == other._:
                return True

            else:
                return False
        elif isinstance(other, (V, F)):
            return C(lhs=self, rhs=other, rel='eq')

        else:
            return False

    def __le__(self, other: Self):

        if isinstance(other, P):
            if isinstance(self._, list) and all(
                [i <= j for i, j in zip(self._, other._)]
            ):
                return True
            elif isinstance(self._, (int, float)) and self._ <= other._:
                return True

            else:
                return False

        elif isinstance(other, (V, F)):
            return C(lhs=self, rhs=other, rel='le')

        else:
            return False

    def __ge__(self, other: Self):
        if isinstance(other, P):
            if isinstance(self._, list) and all(
                [i >= j for i, j in zip(self._, other._)]
            ):
                return True
            elif isinstance(self._, (int, float)) and self._ >= other._:
                return True

            else:
                return False

        else:
            return C(lhs=self, rhs=other, rel='ge')

    def __lt__(self, other: Self):

        if isinstance(other, P):
            if isinstance(self._, list) and all(
                [i < j for i, j in zip(self._, other._)]
            ):
                return True
            elif isinstance(self._, (int, float)) and self._ < other._:
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
            if isinstance(self._, list) and all(
                [i > j for i, j in zip(self._, other._)]
            ):
                return True
            elif isinstance(self._, (int, float)) and self._ > other._:
                return True

            else:
                return False
        else:
            return self >= other

    def __call__(self) -> str:
        return Math(self.latex())
