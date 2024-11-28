"""Continuous Variable
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from math import prod
from functools import reduce

from IPython.display import Math, display
from pyomo.environ import Binary, Integers, NonNegativeIntegers, NonNegativeReals, Reals
from pyomo.environ import Var as PyoVar
from sympy import Idx, IndexedBase, Symbol, symbols

from ..elements.var import Var
from .constraint import C
from .function import F
from ..elements.idx import Idx, X, Skip
from .index import I


if TYPE_CHECKING:
    from .parameter import P


class V:
    """Variable Set"""

    def __init__(
        self,
        *index: tuple[Idx | I],
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
        tag: str = None,
    ):

        self.tag = tag

        # if the variable is an integer variable
        self.itg = itg
        # if the variable is binary
        self.bnr = bnr
        if self.bnr:
            self.itg = bnr
            if not nn:
                raise ValueError('Binary variables must be non-negative')

        # if the variable is non negative
        self.nn = nn
        if index:
            index: I = prod(index)

        self.index = index

        self.name = ''
        # number of the set in the program
        self.n: int = None

        # variables generated at the indices
        # of a variable set are stored here
        # once realized, the values take a int or float value
        # value is determined when mathematical model is solved
        if self.index:
            self._ = [
                Var(
                    **self.args(),
                    parent=self,
                    pos=n,
                )
                for n in range(len(self))
            ]
        else:
            self._ = []

        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False

        self.idx = {idx: var for idx, var in zip(self.index, self._)}

    def args(self) -> dict:
        """Arguments"""
        return {
            'itg': self.itg,
            'nn': self.nn,
            'bnr': self.bnr,
        }

    def fix(self, values: P | list[float]):
        """Fix the value of the variable"""
        # i am not running a type check for Parameter here
        # P imports V
        if isinstance(values, list):
            self._ = values
            self._fixed = True
        else:
            self._ = values._
            self._fixed = True

    def sol(self, aslist: bool = False) -> list[float] | None:
        """Solution"""
        if aslist:
            return [v._ for v in self._]
        for v in self._:
            v.sol()

    def pprint(self, descriptive: bool = False):
        """Display the variables"""
        if descriptive:
            for v in self._:
                if isinstance(v, (int, float)):
                    display(Math(str(v)))
                else:
                    display(Math(v.latex()))
        else:
            display(Math(self.latex()))

    def sympy(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        return IndexedBase(str(self))[
            symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
        ]

    def pyomo(self) -> Var:
        """Pyomo representation"""
        idx = [i.pyomo() for i in self.index]
        if self.bnr:
            return PyoVar(*idx, domain=Binary, doc=str(self))

        elif self.itg:
            if self.nn:
                return PyoVar(*idx, domain=NonNegativeIntegers, doc=str(self))
            else:
                return PyoVar(*idx, domain=Integers, doc=str(self))

        else:
            if self.nn:
                return PyoVar(*idx, domain=NonNegativeReals, doc=str(self))
            else:
                return PyoVar(*idx, domain=Reals, doc=str(self))

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

    def mps(self) -> str:
        """MPS representation"""
        return str(self).upper()

    def lp(self) -> str:
        """LP representation"""
        return str(self)

    def __neg__(self):
        return F(sub=True, two=self)

    def __pos__(self):
        return F(add=True, two=self)

    def __add__(self, other: Self | F):
        if other is None:
            return self
        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self | F):
        if other == 0 or other == 0.0 or other is None:
            return self
        return self + other

    def __sub__(self, other: Self | F):
        if other is None:
            return -self

        if isinstance(other, F):
            return -other + self

        return F(one=self, sub=True, two=other)

    def __rsub__(self, other: Self | F | int):
        if other == 0 or other == 0.0 or other is None:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | F):
        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self | F | int):
        if isinstance(other, (int, float)):
            if other == 1:
                return self
            other = float(other)
        return F(one=other, mul=True, two=self)

    def __truediv__(self, other: Self | F):
        return F(one=self, two=other, div=True)

    def __rtruediv__(self, other: Self | F | int):
        if other == 1:
            return self
        else:
            return self / other

    def __eq__(self, other):
        return C(funcs=self - other)

    def __le__(self, other):
        return C(funcs=self - other, leq=True)

    def __ge__(self, other):
        return C(funcs=other - self, leq=True)

    def __lt__(self, other):
        return self <= other

    def __gt__(self, other):
        return self >= other

    def __iter__(self):
        for i in self.index:
            yield self(i)

    def __pow__(self, other: int):
        f = self
        for _ in range(other - 1):
            f *= self
        return f

    def __call__(self, *key: tuple[X | Idx | I]) -> Self:
        # if the whole set is called
        if prod(key) == self.index:
            return self

        var = V(**self.args(), tag=self.tag)
        var.n = self.n
        var.name = self.name
        # if a subset is called
        if isinstance(prod(key), I):
            var.index = prod(key)
            var._ = [
                self.idx[idx] if not isinstance(idx, Skip) else 0 for idx in prod(key)
            ]
            return var

        # if a single index is called
        key = reduce(lambda a, b: a & b, key)
        var.index = key
        var._ = [self.idx[key]]
        return var

    def __getitem__(self, pos: int) -> Var:
        return self._[pos]

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
