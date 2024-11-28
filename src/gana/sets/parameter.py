"""A Paramter
"""

from typing import Self
from math import prod

from IPython.display import Math, display
from pyomo.environ import Param as PyoParam
from sympy import Idx, IndexedBase, Symbol, symbols

from ..value.bigm import M
from .constraint import C
from .function import F
from .variable import V

from .index import I
from ..elements.idx import Idx, X


class P:
    """A Parameter"""

    def __init__(
        self,
        *index: tuple[Idx | I],
        _: list[int | float | bool] = None,
        tag: str = None,
    ):
        self.tag = tag

        if not _:
            _ = [_]

        self._: list[float | M] = _

        for n, p in enumerate(self._):
            if isinstance(p, bool) and p is True:
                self._[n] = M()
            # convert any into float
            if p:
                self._[n] = float(p)

        self.index: I = prod(index)

        self.name = ''
        # number of the set in the program
        self.n: int = None

    def __setattr__(self, name, value):
        # if negative, already made from another parameter, so
        # do not capitalize
        if name == 'name' and value and isinstance(value, str) and value[0] != '-':
            value = value.capitalize()

        super().__setattr__(name, value)

    def isneg(self):
        """Check if the parameter is negative"""
        return self.name[0] == '-'

    def nsplit(self):
        """Split the name"""
        if '_' in self.name:
            name, sup = self.name.split('_')
            return name, r'^{' + sup + r'}'
        return self.name, ''

    def latex(self) -> str:
        """LaTeX representation"""
        name, sup = self.nsplit()

        return (
            name
            + sup
            + r'_{'
            + rf'{self.index}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def matrix(self):
        """Matrix Representation"""

    def pprint(self):
        """Display the variables"""
        display(Math(self.latex()))

    def sympy(self) -> IndexedBase | Symbol:
        """symbolic representation"""

        return IndexedBase(str(self))[
            symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
        ]

    def pyomo(self) -> PyoParam:
        """Pyomo representation"""
        # idx = [i.pyomo() for i in self.index]
        # return PyoParam(*idx, initialize=self._, doc=str(self))
        return self._

    def __neg__(self):
        # self._ = [-i for i in self._]
        # return self
        p = P(self.index, _=[-i for i in self._])
        if self.isneg():
            p.name = self.name[1:]
        else:
            p.name = r'-' + rf'{self.name}'
        p.n = self.n
        return p
        # return P(*self.index, _=[-i for i in self._])

    def __pos__(self):
        return self

    def __abs__(self):
        return P(*self.index, _=[abs(i) for i in self._])

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
            self._ = [i + j for i, j in zip(self._, other._)]
            return self

        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self):
        return self + other

    def __sub__(self, other: Self):
        if isinstance(other, int) and other == 0:
            return self

        if isinstance(other, P):
            self._ = [i - j for i, j in zip(self._, other._)]
            return self

        return F(one=self, sub=True, two=other)

    def __rsub__(self, other: Self):
        return self - other

    def __mul__(self, other: Self | int | float | V | F):
        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                return self
            if other in [0, 0.0]:
                return 0
        if isinstance(other, P):
            self._ = [i * j for i, j in zip(self._, other._)]
            self.name = f'{self.name} * {other.name}'
            return self
        if isinstance(other, F):
            if other.add:
                return F(one=self * other.one, add=True, two=self * other.two)
            if other.sub:
                return F(one=self * other.one, sub=True, two=self * other.two)
        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self):
        if isinstance(other, int) and other == 1:
            return self
        return other * self

    def __truediv__(self, other: Self):
        if isinstance(other, P):
            return P(*self.index, _=[i / j for i, j in zip(self._, other._)])

        if isinstance(other, F):
            return F(one=self, div=True, two=other)

        if isinstance(other, V):
            return F(one=self, div=True, two=other)

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
        return C(funcs=self - other)

    def __le__(self, other: Self):

        if isinstance(other, P):
            return all([i <= j for i, j in zip(self._, other._)])
        return C(funcs=self - other, leq=True)

    def __ge__(self, other: Self):
        if isinstance(other, P):
            return all([i >= j for i, j in zip(self._, other._)])
        return C(funcs=other - self, leq=True)

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

    def __call__(self, *key: tuple[X | Idx | I]) -> Self:
        if prod(key) == self.index:
            return self

    # def __call__(self, *key: tuple[Idx | I]) -> Self:

    #     if len(key) == 1:
    #         key = key[0]

    #     if key in self.index._:
    #         return self[self.idx[str(key)]]

    #     p = P(*key)
    #     p.n = self.n
    #     p.name = self.name
    #     p._ = [self[self.idx[i]] if not i.skip() else None for i in p.index._]
    #     return p

    def __getitem__(self, pos: int) -> float | int | M:
        return self._[pos]
