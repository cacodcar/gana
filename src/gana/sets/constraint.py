"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from ..elements.cons import Cons
from ..elements.idx import Skip

if TYPE_CHECKING:
    from .function import F


class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions

    Not to be used directly. Made based on relationship between paramter sets, variable sets, or function sets.

    Args:
        funcs (F): Function set
        leq (bool, optional): If the constraint is less than or equal to. Defaults to False.

    Attributes:
        _ (list[Cons]): List of constraints
        funcs (F): Function set
        leq (bool): If the constraint is less than or equal to
        binding (bool): If the constraint is binding
        nn (bool): If the constraint is non-negative
        index (P): Index of the constraint set. Product of all indices.
        eq (bool): If the constraint is an equality constraint
        one (V | P): Element one in the function
        two (V | P): Element two in the function
        name (str): Name of the constraint. Shows the operation.
        n (int): Number of the set in the program
        pname (str): Name given by user in program

    """

    def __init__(
        self,
        funcs: F,
        leq: bool = False,
    ):
        self.variables = funcs.variables

        index = funcs.index
        index.constraints.append(self)
        self.index = index
        self.funcs = funcs

        self.leq = leq

        # since indices should match, take any

        # whether the constraint is binding
        self.binding = False

        if self.funcs.isnegvar and self.leq:
            self.nn = True
        else:
            self.nn = False

        self._ = [
            Cons(parent=self, pos=n, func=f, leq=self.leq, nn=self.nn)
            for n, f in enumerate(self.funcs)
            if f
        ]

        if self.leq:
            self.name = self.funcs.name + r'<=0'

        else:
            self.name = self.funcs.name + r'=0'

        # number of the set in the program
        self.n: int = None

        # name given by user in program
        self.pname: str = None

        # self.struct = self.funcs.struct

    @property
    def A(self) -> list[float | None]:
        """Variable Coefficients"""
        return self.funcs.A

    @property
    def X(self) -> list[None | int]:
        """Variables"""
        return self.funcs.X

    @property
    def B(self) -> float | None:
        """Constant"""
        return self.funcs.B

    @property
    def F(self) -> float | None:
        return self.funcs.F

    @property
    def Z(self) -> float | None:
        return self.funcs.Z

    @property
    def eq(self):
        """Equality Constraint"""
        return not self.leq

    @property
    def one(self):
        """element one in function"""
        return self.funcs.one

    @property
    def two(self):
        """element two in function"""
        return self.funcs.two

    def matrix(self):
        """Matrix Representation"""

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'[{self.n}] {self.funcs.latex()} {rel} 0'

    def pprint(self, descriptive: bool = False):
        """Display the function"""

        if descriptive:
            for c in self._:
                display(Math(c.latex()))
        else:
            display(Math(self.latex()))

    def sol(self):
        """Solution"""
        for c in self._:
            c.sol()

    # TODO
    # def __call__(self, *key: tuple[Idx] | Idx) -> Cons:
    #     if len(key) == 1:
    #         return self._[self.idx[key[0]]]
    #     return self[self.idx[key]]

    def __getitem__(self, pos: int) -> Cons:
        return self._[pos]

    def __iter__(self):
        return iter(self._)

    def order(self) -> list:
        """order"""
        return len(self.index)

    def __len__(self):
        return len(self._)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
