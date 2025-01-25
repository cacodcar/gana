"""Parametric variable
"""

from __future__ import annotations

from functools import reduce
from math import prod
from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from ..elements.idx import Idx, Skip, X
from ..elements.pvar import PVar
from .function import F
from .index import I

if TYPE_CHECKING:
    from .parameter import P
    from .variable import V


class T:
    """Parametric variable Set"""

    def __init__(
        self,
        *index: I,
        _: list[tuple[float]] | tuple[float] = None,
        mutable: bool = False,
        tag: str = None,
    ):
        self.tag = tag
        self.mutable = mutable

        self.index: I = prod(index) if index else index

        if not isinstance(_, list):
            _ = [_]

        if self.index:
            self._ = [PVar(parent=self, pos=n, _=_[n]) for n in range(len(self))]
        else:
            self._ = [(0, 1)]

        self.name = ''
        self.n: int = None

        self.idx = {idx: pvar for idx, pvar in zip(self.index, self._)}

    @property
    def CRa(self):
        """CRa"""
        CRa_UB = [[0] * len(self) for _ in range(len(self))]
        CRa_LB = [[0] * len(self) for _ in range(len(self))]

        for n in range(len(self)):
            CRa_UB[n][n] = 1.0
            CRa_LB[n][n] = -1.0

        CRa_ = []

        for n in range(len(self)):
            CRa_.append(CRa_UB[n])
            CRa_.append(CRa_LB[n])

        return CRa_

    @property
    def CRb(self):
        """CRb"""
        CRb_ = []
        for t in self._:
            CRb_.append(t._[1])
            CRb_.append(-t._[0])

        return CRb_

    @property
    def X(self):
        """Variable positions"""
        return [pvar.n for pvar in self._]

    def pprint(self, descriptive: bool = False):
        """Display the variables
        Args:
            descriptive (bool, optional): Displays all variables in the ordered set. Defaults to False.
        """
        if descriptive:
            for pv in self._:
                if isinstance(pv, (int, float)):
                    display(Math(str(pv)))
                else:
                    display(Math(pv.latex()))
        else:
            display(Math(self.latex()))

    def nsplit(self):
        """Split the name
        If there is an underscore, the name is split into name and superscript
        """
        if '_' in self.name:
            name_ = self.name.split('_')
            if len(name_) == 2:
                return name_[0], r'^{' + name_[1] + r'}'
            elif len(name_) == 3:
                return name_[0], r'^{' + name_[1] + r',' + name_[2] + r'}'
        return self.name, ''

    def latex(self) -> str:
        """LaTeX representation"""
        name, sup = self.nsplit()

        name = r'\theta^' + r'{' + name + r'}'

        return (
            name
            + sup
            + r'_{'
            + rf'{self.index.latex(False)}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def __neg__(self):
        return self * -1

    def __add__(self, other: Self | P | V | F):

        if isinstance(other, int) and other == 0:
            return self

        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self | P | V | F):
        return self + other

    def __sub__(self, other: Self | P | V | F):
        if isinstance(other, int) and other == 0:
            return self

        return F(one=self, sub=True, two=other)

    def __rsub__(self, other: Self | P | V | F):
        return self - other

    def __mul__(self, other: Self | F):
        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self | F | int):
        if isinstance(other, (int, float)):
            if other == 1:
                return self
            other = float(other)
        return F(one=other, mul=True, two=self)

    def __call__(self, *key: tuple[X | Idx | I]) -> Self:

        # if the whole set is called
        if prod(key) == self.index:
            return self

        theta = T(tag=self.tag)
        theta.name, theta.n = self.name, self.n

        # if a subset is called
        if isinstance(prod(key), I):
            theta.index = prod(key)
            theta._ = [
                self.idx[idx] if not isinstance(idx, Skip) else None
                for idx in prod(key)
            ]
            return theta

        # if a single index is called
        if len(key) == 1:
            key = None & key[0]
        else:
            key = reduce(lambda a, b: a & b, key)
        theta.index = key
        theta._ = [self.idx[key]]
        return theta

    def __getitem__(self, pos: int) -> float | int:
        return self._[pos]

    def __iter__(self):
        # do not return from self._
        # V needs to be returned not Var
        for i in self.index:
            yield self(i)

    def __len__(self):
        return len(self.index._)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
