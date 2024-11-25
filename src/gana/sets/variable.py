"""Continuous Variable
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from IPython.display import Math, display
from pyomo.environ import Binary, Integers, NonNegativeIntegers, NonNegativeReals, Reals
from pyomo.environ import Var as PyoVar
from sympy import Idx, IndexedBase, Symbol, symbols

from ..elements.var import Var
from .constraint import C
from .function import F
from .ordered import Set
from ..elements.idx import Idx
from .index import I

if TYPE_CHECKING:
    from .parameter import P


class V(Set):
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

        super().__init__(*index)

        # variables generated at the indices
        # of a variable set are stored here
        # once realized, the values take a int or float value
        # value is determined when mathematical model is solved
        # self._: list[Var] = []
        self._ = [
            Var(
                parent=self,
                pos=n,
                itg=self.itg,
                nn=self.nn,
                bnr=self.bnr,
            )
            for n in range(len(self))
        ]

        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False

    # def __setattr__(self, name, value):

    #     if (
    #         hasattr(self, 'name')
    #         and self.name
    #         and name == 'n'
    #         and isinstance(value, int)
    #         and value >= 0
    #     ):
    #         self._ = [
    #             Var(
    #                 parent=self,
    #                 pos=n,
    #                 itg=self.itg,
    #                 nn=self.nn,
    #                 bnr=self.bnr,
    #             )
    #             for n in range(len(self))
    #         ]

    #     super().__setattr__(name, value)

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
        for i in self._:
            yield i

    def __call__(self, *key: tuple[int | Idx | I]) -> Self:

        key = tuple([Idx(i, I(), i) if isinstance(i, int) else i for i in key])

        if len(key) == 1:
            key = key[0]

        if self.index == key:
            return self

        # if key in self.index:
        #     return self[self.idx[str(key)]]

        try:
            return self[self.idx[str(key)]]

        except KeyError:
            # TODO - do better
            v = V(*key, itg=self.itg, nn=self.nn, bnr=self.bnr)
            v.n = self.n
            v.name = self.name
            v._ = [self[self.idx[i]] if not i.skip() else None for i in v.index._]
            return v

    def __getitem__(self, pos: int) -> Var:
        return self._[pos]
