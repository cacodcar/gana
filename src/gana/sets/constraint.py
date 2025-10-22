"""General Constraint Class"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .cases import FCase

if TYPE_CHECKING:
    from .function import F
    from .index import I
    from .parameter import P
    from .theta import T
    from .variable import V


class C:
    """
    Represents a relationship between Parameters, Variables, or Expressions.

    This class is not intended to be used directly. It is constructed based on
    relationships between parameter sets, variable sets, or function sets.

    :param function: Function set
    :type function: F
    :param leq: If the constraint is less than or equal to. Defaults to False.
    :type leq: bool, optional
    :param parent: Parent constraint set. Defaults to None.
    :type parent: C, optional
    :param pos: Position of the constraint in the set. Defaults to None.
    :type pos: int, optional
    :param nn: If the constraint is non-negative. Defaults to False.
    :type nn: bool, optional

    :ivar _: List of constraints
    :vartype _: list[Cons]
    :ivar function: Function set
    :vartype function: F
    :ivar leq: If the constraint is less than or equal to
    :vartype leq: bool
    :ivar binding: If the constraint is binding
    :vartype binding: bool
    :ivar nn: If the constraint is non-negative
    :vartype nn: bool
    :ivar index: Index of the constraint set (product of all indices)
    :vartype index: P
    :ivar eq: If the constraint is an equality constraint
    :vartype eq: bool
    :ivar one: Element one in the function
    :vartype one: V | P
    :ivar two: Element two in the function
    :vartype two: V | P
    :ivar name: Name of the constraint (shows the operation)
    :vartype name: str
    :ivar n: Number of the set in the program
    :vartype n: int
    :ivar pname: Name given by user in program
    :vartype pname: str

    :raises ValueError: Adding constraints of different types (leq and eq)
    :raises ValueError: Subtracting constraints of different types (leq and eq)
    :raises ValueError: Cannot multiply constraints
    :raises ValueError: Cannot divide constraints
    """

    def __init__(
        self,
        function: F | V,
        leq: bool = False,
        parent: C = None,
        pos: int = None,
        nn: bool = False,
        category: str = "General",
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
        self.args = {"leq": self.leq, "nn": self.nn}

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
            return self.function.name + r"<=0"

        else:
            return self.function.name + r"=0"

    # -----------------------------------------------------
    #                    Helpers
    # -----------------------------------------------------

    def categorize(self, category: str):
        """Categorizes the constraint
        
        :param category: Category name
        :type category: str
        """
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
    def P(self) -> list[None | int]:
        """Variables"""
        return self.function.P

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
        return f"C{self.n}"

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r"\leq"

        else:
            rel = r"="

        return rf"[{self.n}]" + r"\text{   }" + rf"{self.function.latex()} {rel} 0"

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
            return f"{self.function.longname} <= 0"
        return f"{self.function.longname} == 0"

    # -----------------------------------------------------
    #                    Solution
    # -----------------------------------------------------

    def output(self, n_sol: int = 0, compare=False):
        """Solution"""
        if self.leq:
            if compare:
                for c in self._:
                    display(
                        Math(
                            c.function.latex()
                            + r"="
                            + ", ".join(str(val) for val in c.function.X.values())
                        )
                    )

            else:
                for c in self._:
                    display(Math(c.function.latex() + r"=" + rf"{c.function.X[n_sol]}"))

    # -----------------------------------------------------
    #                    Operators
    # -----------------------------------------------------

    def __add__(self, other: V | P | T | F) -> Self:
        if isinstance(other, C):
            if self.leq != other.leq:
                raise ValueError(
                    f"Cannot add constraints with different types: {self.leq} and {other.leq}"
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
                    f"Cannot subtract constraints with different types: {self.leq} and {other.leq}"
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
            raise ValueError("Cannot multiply constraints")
        return C(function=self.function * other, leq=self.leq)

    def __rmul__(self, other: V | P | T | F) -> Self:
        return C(function=self.function * other, leq=self.leq)

    def __truediv__(self, other: V | P | T | F) -> Self:
        if isinstance(other, C):
            raise ValueError("Cannot divide constraints")
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
        try:
            return hash(self.name)
        except AttributeError:
            # Fallback for uninitialized state during unpickling
            return id(self)
