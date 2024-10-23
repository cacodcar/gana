"""A Paramter
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math
from pyomo.environ import Param as PyoParam
from sympy import Idx, IndexedBase, Symbol, symbols

from ..value.bigm import M
from .constraints import C
from .functions import F
from .ordered import ESet
from .variables import V

from .indices import I

if TYPE_CHECKING:
    from ..elements.index import Idx


class P(ESet):
    """A Parameter"""

    def __init__(self, *indices: Idx | I, _: list[int | float | bool]):

        name = None

        super().__init__(*indices, name=name)

        self.indices = indices

        self._: list[float | M] = _

        for n, p in enumerate(self._):
            if isinstance(p, bool) and p is True:
                self._[n] = M()
            # convert any into float
            self._[n] = float(p)

    def __setattr__(self, name, value):

        if name == 'name' and isinstance(value, str) and value:
            value = value.capitalize()

        super().__setattr__(name, value)

    def latex(self) -> str:
        """LaTeX representation"""
        return str(self) + r'_{' + ', '.join(rf'{m}' for m in self.indices) + r'}'

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

    def pyomo(self) -> PyoParam:
        """Pyomo representation"""
        # idx = [i.pyomo() for i in self.order]
        # return PyoParam(*idx, initialize=self._, doc=str(self))
        return self._

    def __neg__(self):
        return P(*self.order, _=[-i for i in self._])

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

    def __mul__(self, other: Self):
        if isinstance(other, P):
            self._ = [i * j for i, j in zip(self._, other._)]
            return self
        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self):
        if isinstance(other, int) and other == 1:
            return self
        return self * other

    def __truediv__(self, other: Self):
        if isinstance(other, P):
            return P(*self.order, _=[i / j for i, j in zip(self._, other._)])

        if isinstance(other, F):
            return F(one=self, div=True, two=other)
        if isinstance(other, V):
            return F(one=self, div=True, two=other)

    def __rtruediv__(self, other: Self):
        return other * self

    def __floordiv__(self, other: Self):

        return P(*self.order, _=[i // j for i, j in zip(self._, other._)])

    def __mod__(self, other: Self):

        return P(*self.order, _=[i % j for i, j in zip(self._, other._)])

    def __pow__(self, other: Self):

        return P(*self.order, _=[i**j for i, j in zip(self._, other._)])

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

    def __call__(self, *key: tuple[Idx] | Idx) -> Self:
        if len(key) == 1:
            return self._[self.idx().index(key[0])]
        return self._[self.idx().index(key)]

    def __getitem__(self, pos: int) -> float | int | M:
        return self._[pos]
