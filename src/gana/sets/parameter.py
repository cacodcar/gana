"""Paramter Set 
"""

from functools import reduce
from itertools import product
from math import prod
from typing import Self

from IPython.display import Math, display

from ..elements.idx import Idx, X, Skip
from .constraint import C
from .function import F
from .index import I
from .variable import V

try:
    from pyomo.environ import Param as PyoParam

    has_pyomo = True
except ImportError:
    has_pyomo = False

try:
    from sympy import Idx, IndexedBase, Symbol, symbols

    has_sympy = True
except ImportError:
    has_sympy = False


class P:
    """Ordered set of parameters

    Args:
        *index (tuple[I], optional): Indices. Defaults to None.
        _ (list[int | float], optional): list of parameters. Defaults to None.
        mutable (bool): If the parameter is mutable
        tag (str): Tag/details

    Attributes:
        index (I): Index of the parameter set. Product of all indices.
        _ (list[int | float]): List of parameters. All converted to float.
        mutable (bool): If the parameter is mutable.
        tag (str): Tag/details.
        name (str): Name, set by the program. Capitalized.
        n (int): Number id, set by the program.
        idx (dict[X | Idx, Var]): Index to parameter mapping.
        isnum (bool): If the parameter set is a single number repeated.

    Raises:
        ValueError: If != operator is used with any other type (not P)
        ValueError: If the parameter values and length of indices do not match
    """

    def __init__(
        self,
        *index: I,
        _: list[float] | float = None,
        mutable: bool = False,
        tag: str = None,
    ):

        if not _:
            isnum = True
            _ = [0]
            name = 0

        elif isinstance(_, (int, float)):
            isnum = True
            name = str(_)
            _ = [float(_)]

        else:
            isnum = False
            # set by program
            name = ''
            _ = [float(p) for p in _]

        if index:
            index: I = prod(index)
            index.parameters.append(self)
            if _ and len(index) != len(_):
                raise ValueError(
                    f"Index mismatch: len(values) ({len(_)}) ! = len(index) ({len(index)})"
                )
        else:
            index = I('i', mutable=mutable)

        # do not make property
        self.idx = {idx: par for idx, par in zip(index, _)}

        # if this is just a single number (float or int)

        self.index = index
        self._ = _  # list of parameters

        self.name = name
        self.isnum = isnum

        self.n: int = None
        self.tag = tag
        self.mutable = mutable

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

        if self.isnum:
            return name
        return (
            name
            + sup
            + r'_{'
            + rf'{self.index.latex(False)}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def pprint(self):
        """Display the variables"""
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
        # idx = [i.pyomo() for i in self.index]
        # return PyoParam(*idx, initialize=self._, doc=str(self))
        if has_pyomo:
            return PyoParam(
                initialize=self._,
                doc=str(self),
            )
        print(
            "pyomo is an optional dependency, pip install gana[all] to get optional dependencies"
        )

    def __neg__(self):

        # self._ = [-i for i in self._]
        # return self
        p = P(
            _=[
                -i if not isinstance(self.index[n], Skip) else 0.0
                for n, i in enumerate(self._)
            ]
        )
        p.index = self.index
        p.isnum = self.isnum
        if self.isneg():
            p.name = self.name[1:]
        else:
            p.name = r'-' + rf'{self.name}'
        p.n = self.n
        return p
        # return P(*self.index, _=[-i for i in self._])

    def __pos__(self):
        if self.isneg():
            p = P(self.index, _=[-i for i in self._])
            p.name = self.name[1:]
            p.n = self.n
            p.isnum = self.isnum
            return p
        else:
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

    def __float__(self):
        if self.isnum:

            return self._[-1]
        return self

    def __add__(self, other: Self):

        if isinstance(other, (int, float)):

            if other == 0:
                return self
            if self.isnum:
                par = P(self.index, _=self._[-1] + other, mutable=self.mutable)
                par.name = f'{float(par)}'
                return par

            par = P(self.index, _=[i + other for i in self._])
            par.name = f'({self.name}+{other})'
            return par

        if isinstance(other, list):
            par = P(self.index, _=[i + j for i, j in zip(self._, other)])
            par.name = f'{self.name}+Prm'
            return par

        if isinstance(other, P):
            if self.isnum and other.isnum:
                return P(
                    self.index + other.index,
                    _=self._[0] + other._[0],
                    mutable=self.mutable,
                )
            par = P(
                self.index + other.index,
                _=[i + j for i, j in zip(self._, other._)],
                mutable=self.mutable,
            )
            par.name = f'{self.name}+{other.name}'
            return par

        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self):
        return self + other

    def __sub__(self, other: Self):

        if isinstance(other, (int, float)):

            if other == 0:
                return self
            if self.isnum:
                par = P(self.index, _=self._[0] - other, mutable=self.mutable)
                par.name = f'{float(par)}'
                return par

            par = P(self.index, _=[i - other for i in self._])
            par.name = f'({self.name}-{other})'
            return par

        if isinstance(other, list):
            par = P(self.index, _=[i + j for i, j in zip(self._, other)])
            par.name = f'{self.name}+Prm'
            return par

        if isinstance(other, P):
            if self.isnum and other.isnum:
                return P(
                    self.index + other.index,
                    _=self._[0] - other._[0],
                    mutable=self.mutable,
                )
            par = P(
                self.index + other.index,
                _=[i - j for i, j in zip(self._, other._)],
                mutable=self.mutable,
            )
            par.name = f'{self.name}+{other.name}'
            return par

        return F(one=self, sub=True, two=other)

    def __rsub__(self, other: Self):
        if isinstance(other, (float, int)):
            if other == 0:
                return -self
        return -self + other

    def __mul__(self, other: Self | int | float | V | F):
        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                return self
            if other in [0, 0.0]:
                return 0

            par = P(
                _=[
                    0 if isinstance(self.index[n], Skip) else i * other
                    for n, i in enumerate(self._)
                ],
                mutable=self.mutable,
            )
            par.index = self.index
            if self.isnum:
                par.name = f'{float(self)}*{other}'
            else:
                par.name = f'{self.name}*{other}'
            return par

        if isinstance(other, list):
            par = P(
                self.index,
                _=[i * j for i, j in zip(self._, other)],
                mutable=self.mutable,
            )
            par.name = f'{self.name}*Prm'
            return par

        if isinstance(other, P):
            name_ = None
            if self.isnum:
                if other.isnum:
                    _ = float(self) * float(other)
                    name_ = f'{float(par)}'
                else:
                    _ = [float(self) * i for i in other._]

            elif other.isnum:
                _ = [i * float(other) for i in self._]

            else:
                _ = [i * j for i, j in zip(self._, other._)]

            if not name_:
                name_ = f'{self.name}*{other.name}'

            par = P(
                self.index,
                _=_,
                mutable=self.mutable,
            )
            par.name = name_
            return par

        if isinstance(other, F):
            if other.add:
                return F(one=self * other.one, add=True, two=self * other.two)
            if other.sub:
                return F(one=self * other.one, sub=True, two=self * other.two)
        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self):
        if isinstance(other, (float, int)):
            if int(other) == 1:
                return self
            return self * other

    def __truediv__(self, other: Self):
        if isinstance(other, P):
            return P(self.index, _=[i / j for i, j in zip(self._, other._)])

        if isinstance(other, F):
            return F(one=self, div=True, two=other)

        if isinstance(other, V):
            return F(one=self, div=True, two=other)

    def __rtruediv__(self, other: Self):
        return other * self

    def __floordiv__(self, other: Self):

        return P(self.index, _=[i // j for i, j in zip(self._, other._)])

    def __mod__(self, other: Self):

        return P(self.index, _=[i % j for i, j in zip(self._, other._)])

    def __pow__(self, other: Self):

        return P(self.index, _=[i**j for i, j in zip(self._, other._)])

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
        return iter(self._)

    def __len__(self):
        return len(self.index._)

    def __call__(self, *key: tuple[X | Idx | I]) -> Self:

        if not key:
            return self

        # if the whole set is called
        if prod(key) == self.index:
            return self

        par = P(tag=self.tag)
        par.name, par.n = self.name, par.n

        # if a subset is called
        if isinstance(prod(key), I):
            par.index = prod(key)
            par._ = [
                self.idx[idx] if not isinstance(idx, Skip) else 0 for idx in prod(key)
            ]
            return par

        # if a single index is called
        if len(key) == 1:
            key = None & key[0]
        else:
            key = reduce(lambda a, b: a & b, key)
        par.index = key
        par._ = [self.idx[key]]
        return par

    def __getitem__(self, pos: int) -> float | int:
        return self._[pos]

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
