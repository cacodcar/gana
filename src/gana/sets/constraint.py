"""General Constraint Class"""

from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from importlib import import_module
from typing import TYPE_CHECKING, Self, TypedDict, Union, cast

from IPython.display import Math, display

from gana.types import Number

from .cases import FCase

if TYPE_CHECKING:
    from .function import CoefficientData, ColumnData, F
    from .index import I
    from .parameter import P
    from .theta import T
    from .variable import V

# Forward references preserve runtime introspection without circular imports.
type ConstraintOperand = Union["V", "P", "T", "F", Number]


class _ConstraintOptions(TypedDict):
    """Only relation and nonnegativity flags are replayed during selection."""

    leq: bool
    nn: bool


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

    # Each set stores scalar rows; a scalar row stores itself as its sole
    # member.
    _: list[C]

    # region Construction and ownership

    def __new__(cls, function=None, *args, **kwargs):
        """Dispatch affine roots before compatibility rows are born."""
        if cls is C:
            native = import_module("gana.backends.native.constraints")
            parent = args[1] if len(args) > 1 else kwargs.get("parent")
            if native.supported(function, parent):
                return object.__new__(native.NativeConstraint)
        return object.__new__(cls)

    def __init__(
        self,
        function: F | V,
        leq: bool = False,
        parent: C | None = None,
        pos: int | None = None,
        nn: bool = False,
        category: str = "General",
    ):
        """Normalize variables to expressions and share their scalar rows."""
        if function.case == FCase.VAR:
            # if the function is a variable, the index needs to be made
            # consistent
            # with what a function index looks lik
            function = cast("V", function).make_function()

        function = cast("F", function)
        # Constructed expressions have coordinates; empty shells retain their
        # existing TypeError here instead of acquiring invented coordinates.
        self.function = function(*cast("tuple | list", function.index))
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
        self.args: _ConstraintOptions = {"leq": self.leq, "nn": self.nn}

        # since indices should match, take any

        # whether the constraint is binding
        self.binding = False

        # position of the constraint in the cons_by of its variables
        self.cons_by_pos: dict[V, int] = {}

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
        self.n: int | None = None

        # name given by user in program
        self.pname: str | None = None

        # category of the constraint
        # constraints can be printed by category
        self.category: str = category

    def update_variables(self):
        """
        Register each row once per variable identity, including repeated terms.
        """
        for cons in self._:
            # Symbolic equality constructs constraints; compare identities
            # instead.
            for v in {id(v): v for v in cons.variables}.values():
                if v is not None:
                    # update cons_by for variables of children in constraint
                    cons.cons_by_pos[v] = len(v.cons_by)
                    v.cons_by.append(cons)
        # for v in self.variables:
        #     if v is not None:
        #         v.cons_by.append(self)

    def unregister_variables(self):
        """
        Detach this set's rows by identity and repair retained row positions.
        """
        removed = {id(row) for row in self._}
        variables = {
            id(v): v for row in self._ for v in row.variables if v is not None
        }
        for variable in variables.values():
            variable.cons_by[:] = [
                row for row in variable.cons_by if id(row) not in removed
            ]
            for position, row in enumerate(variable.cons_by):
                row.cons_by_pos[variable] = position
        for row in self._:
            row.cons_by_pos.clear()

    def categorize(self, category: str):
        """Categorizes the constraint

        :param category: Category name
        :type category: str
        """
        self.category = category
        for c in self._:
            c.category = category

    def copy(self) -> Self:
        """Copy the constraint set"""
        return deepcopy(self)

    # endregion

    # region Indexing and selection

    def __call__(self, *key: list[I]) -> C:
        """Select a concrete C view, returning self for an exact selection."""

        if not key or (key == self.index):
            # if the index is an exact match
            # or no key is passed
            return self

        if self.function.case == FCase.VAR:
            return C(function=self.function(*key), **self.args)
        return C(function=self.function(key), **self.args)

    def __getitem__(self, pos: int) -> C:
        """Return the stored scalar constraint at a positional index."""
        return self._[pos]

    def __iter__(self) -> Iterator[C]:
        """
        Iterate scalar constraints without making the container an iterator.
        """
        return iter(self._)

    def __len__(self):
        return len(self._)

    def order(self) -> int:
        """Return the number of index groups, including an empty domain."""
        return len(self.index or ())

    # endregion

    # region Binary arithmetic

    def __add__(self, other: ConstraintOperand) -> C:
        """
        Combine compatible relations, preserving the existing relation type.
        """
        if isinstance(other, C):
            if self.leq != other.leq:
                _error_message = (
                    f"Cannot add constraints with different types: "
                    f"{self.leq} and {other.leq}"
                )
                raise ValueError(_error_message)
            return C(
                function=self.function + other.function,
                leq=self.leq or other.leq,
                category=self.category,
            )
        return C(
            function=self.function + other,
            leq=self.leq,
            category=self.category,
        )

    def __radd__(self, other: ConstraintOperand) -> C:
        """Return the shifted constraint in either operand order."""
        return self + other

    def __sub__(self, other: ConstraintOperand) -> C:
        """Subtract compatible relations, preserving their relation type."""
        if isinstance(other, C):
            if self.leq != other.leq:
                _error_message = (
                    f"Cannot subtract constraints with different types: "
                    f"{self.leq} and {other.leq}"
                )
                raise ValueError(_error_message)
            return C(
                function=self.function - other.function,
                leq=self.leq or other.leq,
                category=self.category,
            )

        return C(
            function=self.function - other,
            leq=self.leq,
            category=self.category,
        )

    def __rsub__(self, other: ConstraintOperand) -> C:
        """Subtract the constraint function from the left operand."""
        return C(
            function=-self.function + other,
            leq=self.leq,
            category=self.category,
        )

    def __mul__(self, other: ConstraintOperand) -> C:
        """Scale a relation by a numeric operand."""
        if isinstance(other, C):
            _error_message = "Cannot multiply constraints"
            # Preserve the user-selected ValueError compatibility contract.
            raise ValueError(_error_message)  # noqa: TRY004
        return self._scaled_constraint(self.function * other)

    def __rmul__(self, other: ConstraintOperand) -> C:
        """Scale a relation with the numeric operand on the left."""
        return self._scaled_constraint(self.function * other)

    def __truediv__(self, other: ConstraintOperand) -> C:
        """Divide a relation by a numeric operand."""
        if isinstance(other, C):
            _error_message = "Cannot divide constraints"
            # Preserve the user-selected ValueError compatibility contract.
            raise ValueError(_error_message)  # noqa: TRY004
        return self._scaled_constraint(self.function / other)

    def _scaled_constraint(self, function: F | int | None) -> C:
        """Retain row count and alignment when expression scaling returns zero.

        F's scalar-zero shortcut is valid for expressions but a relation
        requires an expression row for each original coordinate. Construct
        the zero product directly to retain that shape on both backends.
        """
        if function is None:
            message = "Constraint scaling requires a numeric operand"
            raise TypeError(message)
        if isinstance(function, int):
            # Resolve the expression class lazily across the F/C import cycle.
            expression = cast(
                "type[F]",
                import_module("gana.sets.function").F,
            )
            function = expression(one=self.function, two=function, mul=True)
        return C(function=function, leq=self.leq)

    # endregion

    # region Constraint metadata

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

    @property
    def redundant_bound(self) -> bool:
        """
        Whether a -v <= 0 row is already implied by declared domain bounds.
        """
        return (
            self.leq
            and self.function.case == FCase.NEGVAR
            and all(variable.nn for variable in self.variables)
        )

    # endregion

    # region Matrix representation

    @property
    def A(self) -> CoefficientData:
        """Return flat scalar coefficients or nested collection rows."""
        return self.function.A

    @property
    def P(self) -> ColumnData:
        """Return scalar column IDs or nested collection rows."""
        return self.function.P

    @property
    def B(self) -> Number | list[Number]:
        """Return a scalar RHS constant or the collection of row constants."""
        return self.function.B

    @property
    def F(self) -> list:
        """Return theta coefficients, nested for a collection of rows."""
        return self.function.F

    @property
    def Z(self) -> list:
        """Return theta column IDs, nested for a collection of rows."""
        return self.function.Z

    @property
    def matrix(self) -> dict:
        """Matrix as dict"""
        return self.function.matrix

    # endregion

    # region Solution and output

    def output(self, n_sol: int = 0, compare=False):
        """Solution"""
        if self.leq:
            if compare:
                for c in self._:
                    display(
                        Math(
                            c.function.latex()
                            + r"="
                            + ", ".join(
                                str(val) for val in c.function.X.values()
                            ),
                        ),
                    )

            else:
                for c in self._:
                    display(
                        Math(
                            c.function.latex()
                            + r"="
                            + rf"{c.function.X[n_sol]}",
                        ),
                    )

    # endregion

    # region Display and export

    @property
    def name(self) -> str:

        if self.leq:
            return self.function.name + r"<=0"

        else:
            return self.function.name + r"=0"

    @property
    def longname(self) -> str:
        """Long name"""
        if self.leq:
            return f"{self.function.longname} <= 0"
        return f"{self.function.longname} == 0"

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r"\leq"

        else:
            rel = r"="

        return (
            rf"[{self.n}]"
            + r"\text{   }"
            + rf"{self.function.latex()} {rel} 0"
        )

    def show(self, descriptive: bool = False):
        """Display the function"""

        if descriptive:
            for c in self._:
                display(Math(c.latex()))
        else:
            display(Math(self.latex()))

    def mps(self):
        """Name in MPS file"""
        return f"C{self.n}"

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

    # endregion
