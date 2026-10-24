"""Continuous Variable"""

from __future__ import annotations

import logging
from itertools import product
from operator import add as add_operands
from typing import TYPE_CHECKING, Literal, Self, Union, cast, overload

from IPython.display import Math, display

from gana.types import Number, NumericList, NumericTuple

from ..storage import parameters as storage
from ..storage import symbols as symbol_storage
from ..utils.draw import draw
from ._element import _E, _ElementArgs
from .birth import make_P, make_T
from .cases import Elem, FCase
from .constraint import C
from .function import F
from .index import I
from .operands import normalize_operand, reject_disequality

logger = logging.getLogger("gana")


if TYPE_CHECKING:
    from .objective import O
    from .parameter import P
    from .theta import T

# try:
#     from pyomo.environ import (
#         Binary,
#         Integers,
#         NonNegativeIntegers,
#         NonNegativeReals,
#         Reals,
#     )
#     from pyomo.environ import Var as PyoVar

#     has_pyomo = True
# except ImportError:
#     has_pyomo = False

# try:
#     from sympy import Idx, IndexedBase, symbols

#     has_sympy = True
# except ImportError:
#     has_sympy = False

# Forward references preserve runtime introspection without circular imports.
type ArithmeticOperand = Union[
    "P",
    "T",
    "F",
    Number,
    NumericTuple,
    NumericList,
]
type IndexedArithmeticOperand = Union[
    "P",
    "T",
    "F",
    Number,
    NumericTuple,
    NumericList,
    I,
]


class _VariableArgs(_ElementArgs):
    """Common constructor metadata extended with variable domain flags."""

    itg: bool
    nn: bool
    bnr: bool


class V(_E["V"]):
    """
    Ordered set of variables (Var).

    :param index: Indices. Defaults to None.
    :type index: I or tuple[I], optional
    :param itg: If the variable set is integer. Defaults to False.
    :type itg: bool, optional
    :param nn: If the variable set is non-negative. Defaults to True.
    :type nn: bool, optional
    :param bnr: If the variable set is binary. Defaults to False.
    :type bnr: bool, optional
    :param mutable: If the variable set is mutable. Defaults to False.
    :type mutable: bool, optional
    :param tag: Tag/details
    :type tag: str
    :param ltx: LaTeX representation of the variable set.
    :type ltx: str

    :ivar index: Index of the variable set (product of all indices)
    :vartype index: I
    :ivar map: Index to variable mapping
    :vartype map: dict[I, V]
    :ivar _: List of variables in the set
    :vartype _: list[V]
    :ivar itg: Integer variable set flag
    :vartype itg: bool
    :ivar nn: Non-negative variable set flag
    :vartype nn: bool
    :ivar bnr: Binary variable set flag
    :vartype bnr: bool
    :ivar mutable: Mutable variable set flag
    :vartype mutable: bool
    :ivar tag: Tag/details
    :vartype tag: str
    :ivar name: Name, set by the program
    :vartype name: str
    :ivar n: Number id, set by the program
    :vartype n: int
    :ivar args: Arguments for making similar variable sets
    :vartype args: dict[str, bool]
    :ivar ltx: LaTeX representation of the variable set
    :vartype ltx: str

    :raises ValueError: If variable is binary and not non-negative
    :raises ValueError: Multiplication by tuple or list of tuples
    :raises ValueError: Division by None, tuple, or list of tuples
    :raises ZeroDivisionError: Division by zero
    :raises ValueError: Division of something by a variable
    :raises ValueError: Raising variable to a power, except 0 or 1
    """

    # V has enough legacy fields that another dictionary key expands every
    # view.
    # Isolate this one link while P/T keep their cheaper default object
    # layouts.
    __slots__ = ("_selection_owner",)
    _compact_staging = True

    if storage.NATIVE:
        __setattr__ = symbol_storage.guard_attribute

    # region Construction and ownership

    def __init__(
        self,
        *index: I,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
        mutable: bool = False,
        tag: str | None = "",
        ltx: str | None = "",
        name: str = "",
    ):
        """
        Initialize variable domains and retain indexed ownership metadata.
        """
        _E.__init__(self, *index, tag=tag, ltx=ltx, mutable=mutable, name=name)

        # integer variable set
        self.itg = itg
        # non-negative variable set
        self.bnr = bnr

        # all binaries are integer variables as well
        if self.bnr:
            self.itg = True
            if not nn:
                # Cannot be non negative and binary
                # {-1, 0, 1} is equivalent to {0, 1, 2}
                _error_message = "Binary variables must be non-negative"
                raise ValueError(_error_message)

        self.nn = nn

        # a variable set of size 1 is a scalar variable
        # these are created at each index in the set
        # their position in the parent set is recorded
        # # Example: if v = V(I('i', 'j')) then v._ = [V(I('i)), V(I('j'))]

        # updated by the constraint
        # what constraints constrain this variable
        self.cons_by: list[C] = []

        # which objectives minimize it (gana is always min)
        self.min_by: list[O] = []

        # Solution numbers key scalar history; omitted unused columns are None.
        self.X: dict[int, Number | None] = {}

        # these keep variables consistent with functions for some operations
        # Take the example of a variable set - parameter set
        # [v0 - 2, v1 - 0, v2 + 4]
        # at positions 0 and 2, we have functions
        # at position 1, v1 - 0 = v1, which is a variable
        # these attribute evades the need for an instance check
        self.variables = [self]
        self.struct = (Elem.V, None)
        self.case = FCase.VAR
        # TODO: check
        self.P = [self.n]

        self.copyof: Self | None = None

        # number of splices of the index set
        self.n_splices = 1

        # this flag tells the function
        # that self in its entirety is being returned on call
        # thus a copy needs to be made in the function
        # this prevents the entirety of self being an element of a function
        # as variables can mutate in gana
        self.make_copy: bool = False

        self.category: str = ""

        # functions to evaluate within critical regions
        self.eval_funcs: dict[int, dict[int, F]] = {}

        # evaluations using parametric solutions
        self.evaluation: dict[int, dict[tuple[float, ...], float]] = {}

    @property
    def args(self) -> _VariableArgs:
        """
        Extend common constructor metadata with the variable domain flags.
        """
        return {
            "itg": self.itg,
            "nn": self.nn,
            "bnr": self.bnr,
            "mutable": self.mutable,
            **super().args,
        }

    def _member_template(self):
        """
        Capture metadata as eager children would see it at registration or
        growth.
        """
        return {"name": self.name, "args": self.args}

    def _new_member(
        self,
        key: tuple,
        position: int,
        number: int,
        *,
        template=None,
    ) -> V:
        """
        Build one accepted coordinate with its final parent, position and ID.
        """
        arguments = self.args if template is None else template["args"]
        name = self.name if template is None else template["name"]
        variable = V(**arguments)
        variable.parent = self
        variable.n, variable.pos = number, position
        variable.name = f"{name}[{position}]"
        variable.index = key
        variable._ = [variable]
        variable.map[key] = variable
        return variable

    def birth_variables(self, mutating: bool = False, n_start: int = 0):
        """
        Populate an unregistered root once; growth creates accepted members
        only.

        Retain the historical mutating argument for callers. Final member
        metadata is now initialized together, including mutation positions.
        """
        del mutating
        if self._:
            return
        if storage.NATIVE:
            symbol_storage.register(self, n_start)
            return
        members = [
            self._new_member(key, pos, n_start + pos)
            for pos, key in enumerate(self.map)
        ]
        self._ = members
        self.map.update(zip(self.map, members))

    def copy(self) -> V:
        """
        Returns a copy of the variable set

        :returns: Copy of the variable set
        :rtype: V
        """
        v = self._new_selection(V(**self.args), tuple(self.index))
        v.case = self.case
        v.copyof = self
        if not symbol_storage.select(self, v):
            v.map = self.map.copy()
            v._ = list(self._)
        return v

    def make_function(self) -> F:
        """
        Make a function

        :returns: Function representing the variable set
        :rtype: F
        """
        return F(
            one=make_P(1, self.index),
            mul=True,
            two=self,
            one_type=Elem.P,
            two_type=Elem.V,
            case=FCase.FVAR,
        )

    @property
    def features_in(self) -> list[C | O]:
        """Constraints and objectives that this variable set is part of"""
        return self.cons_by + self.min_by

    # endregion

    # region Indexing and selection

    def __call__(self, *key: I, make_new: bool = False) -> V:
        """Select shared children, preserving copy flags and missing-key slots.

        Already aligned coordinates need no index unpacking. Keep the shortcut
        inside this method so subclass selection overrides still dispatch.
        New selections are V instances, including when called on a subclass.
        """
        if not make_new:
            if not key or self._matches_index(key):
                # if the index is an exact match
                # or no key is passed
                self.make_copy = True
                return self

        # the check helps to handle if a variable itself is an index
        # we do not want to iterate over the entire variable set
        # but treat the variable as a single index element
        key = self._normalize_index(key)

        # if a subset is passed,
        # first create a product to match
        # the indices

        # indices = product(*key)
        # create a new variable set to return
        v = self._new_selection(V(**self.args), key)
        if not symbol_storage.select(self, v, key):
            # Preserve legacy placeholders for skipped or missing coordinates.
            for index in product(*key):
                try:
                    variable = self.map[index]
                except KeyError:
                    variable = None
                try:
                    v.map[index] = variable
                except TypeError:
                    v.map = {index: variable}
                v._.append(variable)

        return v

    def _matches_index(self, key):
        """Unwrap variable-valued axes before invoking symbolic equality.

        Flat scalar coordinates can compare directly. Either side may contain
        singleton lists used to distinguish a variable axis from its members;
        comparing those lists to a V would construct a constraint instead.
        """
        wrapped = any(isinstance(item, list) for item in key) or any(
            isinstance(item, list) for item in self.index
        )
        if wrapped:
            return self._unpack_index(key) == self._unpack_index(self.index)
        return key == tuple(self.index)

    def __len__(self) -> int:
        # For the love of god
        # Do not change this
        return len(self._)

    # endregion

    # region Unary operations

    def __neg__(self) -> F:
        """Construct the existing normalized multiplication by minus one."""
        # doing this here saves some time
        # let the function know that you are passing something consistent
        # already
        # saves time

        return F(
            one=make_P(-1, self.index),
            mul=True,
            two=self,
            one_type=Elem.P,
            two_type=Elem.V,
            case=FCase.NEGVAR,
            consistent=True,
        )

    # endregion

    # region Arithmetic helpers

    def _coerce_operand(self, other):
        """Wrap numbers and interval literals on the variable's domain."""
        if isinstance(other, (int, float)):
            return make_P(other, self.index)
        if isinstance(other, tuple):
            return make_T(other, self.index)
        if isinstance(other, list):
            return (
                make_T(other) if isinstance(other[0], tuple) else make_P(other)
            )
        return other

    # endregion

    # region Binary arithmetic

    def __add__(self, other):
        """
        Add numeric or symbolic operands using common scalar/list coercion.
        """
        if other is None:
            return self
        other = normalize_operand(other)
        if isinstance(other, (int, float)) and other == 0:
            return self
        return F(one=self, two=self._coerce_operand(other), add=True)

    def __radd__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self | F:
        # radd will only be called by non gana elements
        # default to add
        return self + other

    def __sub__(self, other):
        """
        Subtract aligned operands while preserving the variable coordinates.
        """
        if other is None:
            return self
        other = normalize_operand(other)
        if isinstance(other, (int, float)) and other == 0:
            return self
        return F(one=self, two=self._coerce_operand(other), sub=True)

    def __rsub__(self, other):
        """Subtract this variable in the left operand's numeric order."""
        return -self + other

    def __mul__(self, other):
        """
        Scale by numeric coefficients; reject nonlinear symbolic products.
        """
        other = normalize_operand(other)
        if other is None:
            return None
        if isinstance(other, (int, float)):
            if other == 0:
                return 0.0
            if other == 1:
                return self
            if other == -1:
                return -self
        return F(one=self, two=self._coerce_operand(other), mul=True)

    def __rmul__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self | F | float | tuple[object, ...] | None:
        """Append to coordinate tuples or delegate numeric multiplication."""
        # only called for non gana elements (tuple, list, int, float)
        # multiplication is commutative
        if isinstance(other, tuple):
            if type(other) is tuple:
                return (*other, self)
            # Subclasses retain their addition and need not support iteration.
            return add_operands(other, (self,))

        # list int and float handle by __mul__
        return self * other

    def __truediv__(self, other):
        """Divide by real coefficients after checking every denominator."""
        other = normalize_operand(other)
        if other is None:
            _error_message = "Cannot divide by None"
            raise ValueError(_error_message)
        if isinstance(other, (int, float)) and other == 1:
            return self
        return F(one=self, two=self._coerce_operand(other), div=True)

    def __rtruediv__(
        self,
        other: Self | ArithmeticOperand | None,
    ):
        # TODO nonlinear stuff
        """
        Reject reciprocal variables because their expressions are nonlinear.
        """
        _error_message = (
            "Division of something by a variable, "
            "non-linear operations are not supported yet"
        )
        raise ValueError(_error_message)

    def __pow__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self | float:
        """Accept powers zero and one; reject nonlinear powers."""
        other = normalize_operand(other)
        if other is None:
            # raising to nothing, return self
            return self
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                # variable raised to 0 is 1
                return 1.0
            if other in [1, 1.0]:
                # variable raised to 1 is itself
                return self

        # f = self
        # for _ in range(other - 1):
        #     f *= self
        # return f
        # TODO nonlinear stuff
        _error_message = (
            "Raising variable to a power, non-linear operations "
            "are not supported yet"
        )
        raise ValueError(_error_message)

    # endregion

    # region Comparisons

    def __ne__(self, other):
        """
        Reject symbolic disequality, retaining variable-as-index comparison.
        """
        if isinstance(other, I):
            return self.name != other.name
        return reject_disequality()

    # Symbolic equality deliberately differs from object's bool contract.
    def __eq__(  # type: ignore[override]
        self,
        other: object,
    ) -> C | bool:
        """Build symbolic equality, or compare names for variable indices."""

        if isinstance(other, I):
            # variables can be passed as indices
            return self.name == other.name

        return C(self - cast("Self | ArithmeticOperand | None", other))

    def __lt__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> C:
        return self <= other

    def __le__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> C:
        return C(self - other, leq=True)

    def __gt__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> C:
        return self >= other

    def __ge__(
        self,
        other: Self | ArithmeticOperand | None,
    ):
        return C(other - self, leq=True)

    # endregion

    # region Matrix representation

    @property
    def matrix(self) -> dict:
        """Return scalar coefficients or a separate row for each member."""
        if self.parent:
            return {self.n: 1}

        return {v: v.matrix for v in self._}

    @property
    def A(self) -> list[list[float]]:
        """Generate a diagonal matrix representation of the variable set"""
        return [[1] if self._[i] is not None else [] for i in range(len(self))]

    # endregion

    # region Solution and evaluation

    def f_eval(
        self, *values: Number, n_sol: int = 0, n_cr: int = 0
    ) -> Number | list[Number]:
        """
        Evaluates the variable value as a function of parametric variables

        :param values: values of the parametric variables
        :type values: float | int
        :param n_sol: Solution number. Defaults to 0.
        :type n_sol: int, optional
        :param n_cr: Critical region number. Defaults to 0.
        :type n_cr: int, optional

        :returns: evaluated scalar or collection values
        :rtype: int | float | list[int | float]
        """
        return self.eval_funcs[n_sol][n_cr].eval(*values)

    def eval(self, *theta_vals: float, n_sol: int = 0) -> float | None:
        """
        Evaluates the variable value as a function of parametric variables


        :param theta_vals: values of the parametric variables
        :type theta_vals: float
        :param n_sol: solution number. Defaults to 0.
        :type n_sol: int, optional
        :param roundoff: round off the evaluated value. Defaults to 4.
        :type roundoff: int, optional

        :returns: evaluated value
        :rtype: float | None
        """

        try:
            return self.evaluation[n_sol][theta_vals]
        except KeyError:
            logger.warning(
                "⛔ Run program.eval %s "
                "for appropriate solution number first ⛔",
                theta_vals,
            )
            # Preserve the existing missing-solution result explicitly.
            return None

    @overload
    def output(
        self,
        n_sol: int = 0,
        *,
        aslist: Literal[True],
        asdict: bool = False,
        compare: Literal[False] = False,
    ) -> list[Number | None]:
        """List output preserves values and omitted-column placeholders."""
        ...

    @overload
    def output(
        self,
        n_sol: int = 0,
        aslist: bool = False,
        asdict: bool = False,
        compare: bool = False,
    ) -> list[Number | None] | dict[tuple[I, ...], Number | None] | None:
        """Support display, dictionary output and dynamic output choices."""
        ...

    def output(
        self,
        n_sol: int = 0,
        aslist: bool = False,
        asdict: bool = False,
        compare=False,
    ) -> list[Number | None] | dict[tuple[I, ...], Number | None] | None:
        """
        Solution

        :param n_sol: Solution number. Defaults to 0.
        :type n_sol: int, optional
        :param aslist: Returns values taken as list. Defaults to False.
        :type aslist: bool, optional
        :param asdict: Returns values taken as dictionary. Defaults to False.
        :type asdict: bool, optional
        :param compare: Compare solutions across objectives. Defaults to False.
        :type compare: bool, optional


        :returns: Stored solution values, including None for omitted columns.
        :rtype: list[Number | None] | dict[tuple[I, ...], Number | None] | None
        """
        if compare:
            self._display_solutions(n_sol, compare=True)
            return None
        if aslist:
            return [v.X[n_sol] for v in self._ if n_sol in v.X]
        if asdict:
            return {
                idx: v.X[n_sol] for idx, v in self.map.items() if n_sol in v.X
            }
        self._display_solutions(n_sol, compare=False)
        return None

    def _display_solutions(self, n_sol: int, *, compare: bool) -> None:
        """Display all stored solutions or available values for one solution.

        Comparison includes members with no stored values, preserving their
        empty right-hand side. Ordinary display skips missing values.
        """
        for variable in self._:
            if compare:
                value = ", ".join(str(val) for val in variable.X.values())
            elif n_sol in variable.X:
                value = str(variable.X[n_sol])
            else:
                continue
            display(Math(variable.latex() + r"=" + value))

    def report(self) -> V:
        """Return a reporting binary variable

        :returns: Reporting binary variable
        :rtype: V
        """
        return V(
            *self.index,
            bnr=True,
            tag=f"Reporting binary for {self.tag}",
            ltx=rf"x_{self.ltx}",
        )

    # endregion

    # region Display and export

    @property
    def ltx(self) -> str | None:
        """
        Render a collection in bold and preserve a child's inherited symbol.
        """

        if self.parent:
            return self._ltx

        return r"{\mathbf{" + self._latex_name() + r"}}"

    @property
    def index_ltx(self) -> str:
        """Render grouped coordinates before inspecting singleton axes."""
        if isinstance(self.index, set):
            groups = (",".join(i.ltx for i in idx) for idx in self.index)
            return "(" + ")|(".join(groups) + ")"
        if len(self.index) == 1:
            try:
                return self.index[0].ltx
            except AttributeError:
                # if index is of the type ((a,b),)
                self.index = tuple(*self.index)

        return ",".join(
            i.ltx if not isinstance(i, (list, tuple)) else i[0].ltx
            for i in self.index
        )

    def latex(self) -> str:
        """
        LaTeX representation
        :returns: LaTeX representation of the variable set
        :rtype: str
        """
        # Registered members inherit a resolved label; manually erased labels
        # retain their existing concatenation failure.
        return cast(str, self.ltx) + r"_{" + self.index_ltx + r"}"

    def mps(self) -> str:
        """Name in MPS file

        :returns: Name in MPS file
        :rtype: str
        """
        if self.bnr:
            return f"X{self.n}"
        return f"V{self.n}"

    def lp(self) -> str:
        """LP representation

        :returns: LP representation
        :rtype: str
        """
        return f"{self}_{self.pos}"

    # endregion

    # region Plotting

    def line(
        self,
        font_size: float = 16,
        fig_size: tuple[float, float] = (12, 6),
        linewidth: float = 0.7,
        color: str = "blue",
        grid_alpha: float = 0.3,
        usetex: bool = True,
        str_idx_lim: int = 10,
    ):
        """
        Plot the variable set

        :param font_size: Font size for the plot. Defaults to 16.
        :type font_size: float, optional
        :param fig_size: Size of the figure. Defaults to (12, 6).
        :type fig_size: tuple[float, float], optional
        :param linewidth: Width of the line in the plot. Defaults to 0.7.
        :type linewidth: float, optional
        :param color: Color of the line in the plot. Defaults to 'blue'.
        :type color: str, optional
        :param grid_alpha: Transparency of the grid lines. Defaults to 0.3.
        :type grid_alpha: float, optional
        :param usetex: Use LaTeX for text rendering. Defaults to True.
        :type usetex: bool, optional
        :param str_idx_lim: Limit for string indices display. Defaults to 10.
        :type str_idx_lim: int, optional
        """
        draw(
            element=self,
            data=self.output(aslist=True),
            kind="line",
            font_size=font_size,
            fig_size=fig_size,
            linewidth=linewidth,
            color=color,
            grid_alpha=grid_alpha,
            usetex=usetex,
            str_idx_lim=str_idx_lim,
        )

    def bar(
        self,
        font_size: float = 16,
        fig_size: tuple[float, float] = (12, 6),
        linewidth: float = 0.7,
        color: str = "blue",
        grid_alpha: float = 0.3,
        usetex: bool = True,
        str_idx_lim: int = 10,
    ):
        """
        Plot the variable set

        :param font_size: Font size for the plot. Defaults to 16.
        :type font_size: float, optional
        :param fig_size: Size of the figure. Defaults to (12, 6).
        :type fig_size: tuple[float, float], optional
        :param linewidth: Width of the line in the plot. Defaults to 0.7.
        :type linewidth: float, optional
        :param color: Color of the line in the plot. Defaults to 'blue'.
        :type color: str, optional
        :param grid_alpha: Transparency of the grid lines. Defaults to 0.3.
        :type grid_alpha: float, optional
        :param usetex: Use LaTeX for text rendering. Defaults to True.
        :type usetex: bool, optional
        :param str_idx_lim: Limit for string indices display. Defaults to 10.
        :type str_idx_lim: int, optional
        """
        draw(
            element=self,
            data=self.output(aslist=True),
            kind="bar",
            font_size=font_size,
            fig_size=fig_size,
            linewidth=linewidth,
            color=color,
            grid_alpha=grid_alpha,
            usetex=usetex,
            str_idx_lim=str_idx_lim,
        )

    # endregion

    # region Legacy export sketches

    # def sympy(self):
    #     """symbolic representation"""
    #     if has_sympy:
    #         return IndexedBase(str(self))[
    #             symbols(",".join([f"{d}" for d in self.index]), cls=Idx)
    #         ]
    #     logger.warning(
    # "sympy is an optional dependency, pip install gana[all] to get optional
    # dependencies"
    #     )

    # def pyomo(self):
    #     """Pyomo representation"""
    #     if has_pyomo:
    #         idx = [i.pyomo() for i in self.index]
    #         if self.bnr:
    #             return PyoVar(*idx, domain=Binary, doc=str(self))

    #         elif self.itg:
    #             if self.nn:
    # return PyoVar(*idx, domain=NonNegativeIntegers, doc=str(self))
    #             else:
    #                 return PyoVar(*idx, domain=Integers, doc=str(self))

    #         else:
    #             if self.nn:
    # return PyoVar(*idx, domain=NonNegativeReals, doc=str(self))
    #             else:
    #                 return PyoVar(*idx, domain=Reals, doc=str(self))
    #     logger.warning(
    # "pyomo is an optional dependency, pip install gana[all] to get optional
    # dependencies"
    #     )

    # endregion
