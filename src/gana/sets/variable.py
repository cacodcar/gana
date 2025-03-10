"""Continuous Variable
"""

from __future__ import annotations

from functools import reduce
from math import prod
from typing import TYPE_CHECKING, Any, Self

from IPython.display import Math, display

from ..elements.idx import Idx, Skip, X
from ..elements.var import Var
from .constraint import C
from .function import F
from .index import I

if TYPE_CHECKING:
    from .parameter import P

try:
    from pyomo.environ import (Binary, Integers, NonNegativeIntegers,
                               NonNegativeReals, Reals)
    from pyomo.environ import Var as PyoVar

    has_pyomo = True
except ImportError:
    has_pyomo = False

try:
    from sympy import Idx, IndexedBase, Symbol, symbols

    has_sympy = True
except ImportError:
    has_sympy = False


class V:
    """Ordered set of variables (Var)

    Args:
        *index (tuple[I], optional): Indices. Defaults to None.
        itg (bool, optional): If the variable set is integer. Defaults to False.
        nn (bool, optional): If the variable set is non-negative. Defaults to True.
        bnr (bool, optional): If the variable set is binary. Defaults to False.
        mutable (bool, optional): If the variable set is mutable. Defaults to False.
        tag (str): Tag/details


    Attributes:
        index (I): Index of the variable set. Product of all indices.
        _ (list[Var]): List of variables in the set.
        itg (bool): Integer variable set.
        nn (bool): Non-negative variable set.
        bnr (bool): Binary variable set.
        mutable (bool): Mutable variable set.
        tag (str): Tag/details.
        name (str): Name, set by the program.
        n (int): Number id, set by the program.
        idx (dict[X | Idx, Var]): Index to variable mapping.
        args (dict[str, bool]): Arguments to pass when making similar variable sets. itg, nn, bnr.

    Raises:
        ValueError: If variable is binary and not non-negative
        ValueError: Does not support != operation
    """

    def __init__(
        self,
        *index: I,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
        mutable: bool = False,
        tag: str = None,
    ):

        self.tag = tag
        self.itg = itg
        self.bnr = bnr

        if self.bnr:
            self.itg = bnr
            if not nn:
                raise ValueError('Binary variables must be non-negative')

        self.nn = nn
        self.mutable = mutable

        # Matrix of coefficients

        index: I = prod(index) if index else I('i', mutable=mutable)

        index.variables.append(self)
        self.index = index

        # self.A = [[0] * len(self) for _ in range(len(self))]

        # for i in range(len(self)):
        #     self.A[i][i] = 1

        # variables generated at the indices
        # of a variable set are stored here
        # once realized, the values take a int or float value
        # value is determined when mathematical model is solved
        if self.index:
            self._ = [
                Var(
                    itg=self.itg,
                    nn=self.nn,
                    bnr=self.bnr,
                    parent=self,
                    pos=n,
                )
                for n in range(len(self))
            ]
        else:
            self._ = []

        # do not make property
        self.idx = {idx: var for idx, var in zip(self.index, self._)}
        self.args = {'itg': self.itg, 'nn': self.nn, 'bnr': self.bnr}

        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False

        # set by program
        self.name = ''
        self.n: int = None

    def fix(self, values: P | list[float]):
        """Fix the value of the variable
        Args:
            values (P | list[float]): Values to fix the variable
        """
        # i am not running a type check for Parameter here
        # P imports V
        if isinstance(values, list):
            self._ = values
            self._fixed = True
        else:
            self._ = values._
            self._fixed = True

    def sol(self, aslist: bool = False) -> list[float] | None:
        """Solution
        Args:
            aslist (bool, optional): Returns values taken as list. Defaults to False.
        """
        if aslist:
            return [v._ for v in self._]
        for v in self._:
            v.sol()

    def pprint(self, descriptive: bool = False):
        """Display the variables
        Args:
            descriptive (bool, optional): Displays all variables in the ordered set. Defaults to False.
        """
        if descriptive:
            for v in self._:
                if isinstance(v, (int, float)):
                    display(Math(str(v)))
                else:
                    display(Math(v.latex()))
        else:
            display(Math(self.latex()))

    def sympy(self):
        """symbolic representation"""
        if has_sympy:
            return IndexedBase(str(self))[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        print(
            "sympy is an optional dependency, pip install gana[all] to get optional dependencies"
        )

    def pyomo(self):
        """Pyomo representation"""
        if has_pyomo:
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
        print(
            "pyomo is an optional dependency, pip install gana[all] to get optional dependencies"
        )

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

        return (
            name
            + sup
            + r'_{'
            + rf'{self.index.latex(False)}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def mps(self) -> str:
        """MPS representation"""
        return str(self).upper()

    def lp(self) -> str:
        """LP representation"""
        return str(self)

    def __neg__(self):
        from .parameter import P

        # doing this here saves some time
        # p = P(self.index, _=[None if isinstance(_, Skip) else -1.0 for _ in self.index ])
        p = P(_=[-1.0] * len(self))
        p.index = self.index
        # dont pass index during declaration since its already processed
        p.name = '-1'
        # let the function know that you are passing something consistent already
        # saves time
        f = F(one=p, mul=True, two=self, consistent=True)
        f.isnegvar = True
        return f

    def __pos__(self):
        f = F(add=True, two=self, consistent=True)
        return f

    def __ne__(self, other: Any):
        raise TypeError(f"unsupported operand type(s) for !=: 'P' and '{type(other)}'")

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

        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                return self

            elif other in [0, 0.0]:
                return 0.0

            other = float(other)
        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self | F | int):
        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                return self

            elif other in [0, 0.0]:
                return 0.0

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

    def __pow__(self, other: int):
        f = self
        for _ in range(other - 1):
            f *= self
        return f

    def __iter__(self):
        # do not return from self._
        # V needs to be returned not Var
        for i in self.index:
            yield self(i)

    def __len__(self):
        if self.index:
            return len(self.index)
        return 1

    def __call__(self, *key: tuple[X | Idx | I]) -> Self:

        if not key:
            return self

        prodkey = prod(key)

        # if the whole set is called
        if prodkey == self.index:
            return self

        var = V(**self.args, tag=self.tag, mutable=self.mutable)
        var.name, var.n = self.name, self.n
        # if a subset is called
        if isinstance(prodkey, I):
            var.index = prodkey
            var._ = [
                self.idx[idx] if not isinstance(idx, Skip) else None for idx in prodkey
            ]
            return var

        # if a single index is called
        if len(key) == 1:
            key = None & key[0]
        else:
            key = reduce(lambda a, b: a & b, key)
        key = 1 * key
        var.index = key
        var._ = [self.idx[key]]
        return var

    def __getitem__(self, pos: int) -> Var:
        return self._[pos]

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
