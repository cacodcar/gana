"""General Constraint Class"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .cases import FCase
from copy import deepcopy

if TYPE_CHECKING:
    from .function import F
    from .parameter import P
    from .theta import T
    from .variable import V
    from .index import I


class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions

    Not to be used directly. Made based on relationship between parameter sets, variable sets, or function sets.

    Args:
        function (F): Function set
        leq (bool, optional): If the constraint is less than or equal to. Defaults to False.
        parent (C, optional): Parent constraint set. Defaults to None.
        pos (int, optional): Position of the constraint in the set. Defaults to None.
        nn (bool, optional): If the constraint is non-negative. Defaults to False.

    Attributes:
        _ (list[Cons]): List of constraints
        function (F): Function set
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

    Raise:
        ValueError: Add constraints of different types (leq and eq)
        ValueError: Substract constraints of different types (leq and eq)
        ValueError: Cannot multiply constraints
        ValueError: Cannot divide constraints
    """

    def __init__(
        self,
        function: F | V,
        leq: bool = False,
        parent: C = None,
        pos: int = None,
        nn: bool = False,
        category: str = 'General',
    ):
        if function.case == FCase.VAR:
            # if the function is a variable, the index needs to be made consistent
            # with what a function index looks lik
            function = function.make_function()

        self.function = function(*function.index)
        self.index = function.index
        # variables in the constraint
        self.variables = function.variables
        # index is the same as the function

        # whether the constraint is less than or equal to
        self.leq = leq

        # the map of indices and constraints
        self.map = function.map
        # and the structure
        self.struct = function.struct

        # if part of a constraint set
        self.parent = parent

        # position in the parent set
        self.pos = pos
        # if its a non-negativity constraint for a variable
        self.nn = nn

        # arguments to pass
        self.args = {'leq': self.leq, 'nn': self.nn}

        # since indices should match, take any

        # whether the constraint is binding
        self.binding = False

        # position of the constraint in the cons_by of its variables
        self.cons_by_pos = {}

        if not self.nn:
            if self.function.case == FCase.NEGVAR and self.leq:
                self.nn = True
            else:
                self.nn = False

        if self.parent is None:
            # if this is a constraint set, birth constraints
            self._ = [
                C(function=f, leq=self.leq, parent=self, pos=n, nn=self.nn)
                for n, f in enumerate(self.function)
                if f
            ]
        else:
            # single constraint of a constraint set
            self._ = [self]

        # number of the set in the program
        self.n: int = None

        # name given by user in program
        self.pname: str = None

        # category of the constraint
        # constraints can be printed by category
        self.category: str = category

    @property
    def name(self) -> str:

        if self.leq:
            return self.function.name + r'<=0'

        else:
            return self.function.name + r'=0'

    # -----------------------------------------------------
    #                    Helpers
    # -----------------------------------------------------

    def categorize(self, category: str):
        """Categorizes the constraint"""
        self.category = category
        for c in self._:
            c.category = category

    def update_variables(self):
        """Update variables in the constraint set"""
        for cons in self._:
            for v in cons.variables:
                if v is not None:
                    # update cons_by for variables of children in constraint
                    cons.cons_by_pos[v] = len(v.cons_by)
                    v.cons_by.append(cons)
        # for v in self.variables:
        #     if v is not None:
        #         v.cons_by.append(self)

    def copy(self) -> Self:
        """Copy the constraint set"""
        return deepcopy(self)

    # -----------------------------------------------------
    #                    Matrices
    # -----------------------------------------------------

    @property
    def A(self) -> list[float | None]:
        """Variable Coefficients"""
        return self.function.A

    @property
    def X(self) -> list[None | int]:
        """Variables"""
        return self.function.X

    @property
    def B(self) -> float | None:
        """Constant"""
        return self.function.B

    @property
    def F(self) -> float | None:
        return self.function.F

    @property
    def Z(self) -> float | None:
        return self.function.Z

    @property
    def matrix(self) -> dict:
        """Matrix as dict"""
        return self.function.matrix

    # -----------------------------------------------------
    #                    Form
    # -----------------------------------------------------

    @property
    def eq(self):
        """Equality Constraint"""
        return not self.leq

    @property
    def one(self):
        """element one in function"""
        return self.function.one

    @property
    def two(self):
        """element two in function"""
        return self.function.two

    # -----------------------------------------------------
    #                    Printing
    # -----------------------------------------------------

    def mps(self):
        """Name in MPS file"""
        return f'C{self.n}'

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'[{self.n}]' + r'\text{   }' + rf'{self.function.latex()} {rel} 0'

    def show(self, descriptive: bool = False):
        """Display the function"""

        if descriptive:
            for c in self._:
                display(Math(c.latex()))
        else:
            display(Math(self.latex()))

    @property
    def longname(self) -> str:
        """Long name"""
        if self.leq:
            return f'{self.function.longname} <= 0'
        return f'{self.function.longname} == 0'

    # -----------------------------------------------------
    #                    Solution
    # -----------------------------------------------------

    def sol(self):
        """Solution"""
        for c in self._:
            if self.leq:
                display(Math(c.function.latex() + r'=' + rf'{c.function.value}'))

    # -----------------------------------------------------
    #                    Operators
    # -----------------------------------------------------

    def __add__(self, other: V | P | T | F) -> Self:
        if isinstance(other, C):
            if self.leq != other.leq:
                raise ValueError(
                    f'Cannot add constraints with different types: {self.leq} and {other.leq}'
                )
            return C(
                function=self.function + other.function,
                leq=self.leq or other.leq,
                category=self.category,
            )
        return C(function=self.function + other, leq=self.leq, category=self.category)

    def __radd__(self, other: V | P | T | F) -> Self:
        _ = self + other

    def __sub__(self, other: V | P | T | F) -> Self:

        if isinstance(other, C):
            if self.leq != other.leq:
                raise ValueError(
                    f'Cannot subtract constraints with different types: {self.leq} and {other.leq}'
                )
            return C(
                function=self.function - other.function,
                leq=self.leq or other.leq,
                category=self.category,
            )

        return C(function=self.function - other, leq=self.leq, category=self.category)

    def __rsub__(self, other: V | P | T | F) -> Self:
        _ = self - other

    def __mul__(self, other: V | P | T | F) -> Self:
        if isinstance(other, C):
            raise ValueError('Cannot multiply constraints')
        return C(function=self.function * other, leq=self.leq)

    def __rmul__(self, other: V | P | T | F) -> Self:
        return C(function=self.function * other, leq=self.leq)

    def __truediv__(self, other: V | P | T | F) -> Self:
        if isinstance(other, C):
            raise ValueError('Cannot divide constraints')
        return C(function=self.function / other, leq=self.leq)

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __call__(self, *key: list[I]) -> Self:

        if not key or (key == self.index):
            # if the index is an exact match
            # or no key is passed
            return self

        if self.function.case == FCase.VAR:
            return C(function=self.function(*key), **self.args)
        return C(function=self.function(key), **self.args)

    def __getitem__(self, pos: int) -> Self:
        return self._[pos]

    def __iter__(self) -> Self:
        return iter(self._)

    def order(self) -> list:
        """order"""
        return len(self.index)

    def __len__(self):
        return len(self._)

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
