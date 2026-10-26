"""Function Set"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import cached_property
from importlib import import_module
from itertools import repeat
from operator import add as add_operands
from typing import TYPE_CHECKING, Self, Union, cast, overload

from IPython.display import Math, display

from gana.types import Number, NumericList, NumericTuple

from .birth import make_P, make_T
from .cases import Elem, FCase
from .constraint import C
from .index import I
from .operands import NumericDispatch, normalize_operand, reject_disequality

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from .parameter import P
    from .theta import T
    from .variable import V

# Forward references preserve runtime introspection without circular imports.
type ExpressionSet = Union["V", "P", "T"]
type FunctionInput = Union[Number, list[Number], "P", "V", "T"]
type ThetaTerm = tuple["T", tuple, Number]
# Public inputs are normalized before collection alignment. Scalar rows then
# replace parameter containers with numbers; empty shells retain None.
type SymbolicOperand = Union["F", ExpressionSet]
type StoredOperand = SymbolicOperand | Number | None
type RowOperand = StoredOperand | tuple[Number, ...]
type ReductionInfo = tuple[Union["V", "F"], I | tuple | None, int | None]
type CoefficientData = list[Number] | list[list[Number]]
type ColumnData = list[int | None] | list[list[int | None]]
# Matrix fields F and P shadow class names in class-scope annotations.
type FunctionNode = Union["F"]
type ParameterSet = Union["P"]

type ArithmeticOperand = Union[
    "V",
    "P",
    "T",
    Number,
    NumericTuple,
    NumericList,
]

# Additional positional arguments belong to the legacy constructor's options.
_BINARY_OPERANDS = 2


class F(NumericDispatch):
    r"""
    Provides relational operations between parameter, variable, parametric
    variable,
    or function sets (F).

    This class is not intended to be declared by the user directly.
    It is constructed based on operations between parameter sets (P or list of
    numbers or number),
    variable sets (V), or function sets (F).

    :param one: First element.
    :type one: int | float | list[int | float] | P | V | T | F, optional
    :param two: Second element. Defaults to 0.
    :type two: int | float | list[int | float] | P | V | T | F, optional
    :param one_type: Type of `one`. Defaults to None.
    :type one_type: Elem, optional
    :param two_type: Type of `two`. Defaults to None.
    :type two_type: Elem, optional
    :param mul: Multiplication operation. Defaults to False.
    :type mul: bool, optional
    :param add: Addition operation. Defaults to False.
    :type add: bool, optional
    :param sub: Subtraction operation. Defaults to False.
    :type sub: bool, optional
    :param div: Division operation. Defaults to False.
    :type div: bool, optional
    :param consistent: If the function is already consistent, saves
        computation. Defaults to False.
    :type consistent: bool, optional
    :param case: Special function case. Defaults to None.
    :type case: FCase, optional
    :param parent: Parent function. Defaults to None.
    :type parent: Self, optional
    :param pos: Position of the function in the parent. Defaults to None.
    :type pos: int, optional
    :param index: Index of the function. Defaults to None.
    :type index: tuple[I] | list[tuple[I]] | None, optional
    :param issumhow: If the function is a summation, provides variable, index,
        and position. Defaults to None.
    :type issumhow: tuple[V, I, int], optional
    :param process: Whether to make matrices. Defaults to True.
    :type process: bool, optional

    :ivar one: First element
    :vartype one: P | V | F
    :ivar two: Second element
    :vartype two: P | V | F
    :ivar mul: Multiplication flag
    :vartype mul: bool
    :ivar add: Addition flag
    :vartype add: bool
    :ivar sub: Subtraction flag
    :vartype sub: bool
    :ivar div: Division flag
    :vartype div: bool
    :ivar rel: Relation symbol
    :vartype rel: str
    :ivar name: Name of the function, describing the operation
    :vartype name: str
    :ivar index: Index of the function set
    :vartype index: I
    :ivar array: List of elements in the function
    :vartype array: list[P | T | V]
    :ivar vars: List of variables in the function
    :vartype vars: list[V]
    :ivar struct: Structure of the function
    :vartype struct: tuple[Elem, Elem]
    :ivar rels: Relations in the function
    :vartype rels: list[str]
    :ivar elms: Elements in the function
    :vartype elms: list[P | V]
    :ivar isnegvar: If the function is :math:`-1 \cdot v` (negation)
    :vartype isnegvar: bool
    :ivar isconsistent: If the function is consistent
    :vartype isconsistent: bool
    :ivar n: Number id, set by the program
    :vartype n: int
    :ivar pname: Name set by the program
    :vartype pname: str
    :ivar elmo: Elements with relation (also a sesame street character)
    :vartype elmo: dict[int, list[P | V | T | str]]

    :raises ValueError: If none of `mul`, `add`, `sub`, or `div` is True
    """

    # Retain theta owner/coordinate references until registration.
    # Empty and legacy sum rows have no parametric terms.
    _theta_terms: Sequence[ThetaTerm] = ()
    _theta_rows: Sequence[Sequence[ThetaTerm]] = ()
    _row_layout: tuple[tuple, tuple]
    rhs_thetas: list[T]
    B: list[Number] | Number
    # Scalar rows use flat lists; root collections retain lists of those rows.
    A: CoefficientData
    F: CoefficientData
    P: ColumnData
    Z: ColumnData
    # Legacy scratch metadata remains independently mutable on each row.
    Y: list[object]
    variables: list[V]
    mul_parameters: list[ParameterSet]
    rhs_parameters: list[ParameterSet]
    map: dict[tuple, FunctionNode | None]
    one: StoredOperand
    two: StoredOperand
    one_type: Elem | None
    two_type: Elem | None
    _one: Sequence[RowOperand]
    _two: Sequence[RowOperand]
    # Composite coordinates retain nested axes and custom tuple contents.
    index: tuple[object, ...] | list[tuple] | None
    # Naming and empty-row initialization share this program-assigned label.
    pname: str
    # Row keys use dictionaries or broadcast lists; skipped keys may be None.
    _one_map: Collection
    _two_map: Collection

    # region Construction and normalization

    def __new__(cls, *args, **kwargs):
        """Use native affine batches for supported base-class operands."""
        if cls is F:
            if len(args) <= _BINARY_OPERANDS:
                factory = import_module(
                    "gana.backends.native.algebra",
                ).try_build
                result = factory(*args, **kwargs)
                if result is not None:
                    return result
        return object.__new__(cls)

    def __init__(
        self,
        # ------Elements -----------
        one: Self | FunctionInput | None = None,
        two: Self | FunctionInput | None = None,
        # --------- Types --------------
        one_type: Elem | None = None,
        two_type: Elem | None = None,
        # ------- Relations -----------
        mul: bool = False,
        add: bool = False,
        sub: bool = False,
        div: bool = False,
        # ------ Vector ---------------
        parent: Self | None = None,
        pos: int | None = None,
        index: tuple[I] | list[tuple[I]] | None = None,
        # ------- Other attributes -----
        case: FCase | None = None,
        consistent: bool = False,
        issumhow: ReductionInfo | None = None,
    ):
        """
        Initialize a row container, capturing mutable variable membership.
        """
        # Registration assigns ownership, coordinates and a model number.
        self.parent = parent
        self.pos = pos
        self.n: int | None = None
        self._: list[F | None] = []
        self.map = {}
        self.index = index
        self.case = case
        self.consistent = consistent
        self.issumhow = issumhow
        self._initialize_evaluation()

        if self.issumhow:
            # This legacy reduction branch labels its operands F and V below.
            self._capture_reduction(cast("F", one), cast("V", two))
            self.handle_rel(mul, add, sub, div, ignore=True)

            self.one_type = Elem.F
            self.two_type = Elem.V
            self.make_args()
            self._initialize_empty_rows()

        elif one is not None or two is not None:
            # A basic Function is of the type
            # P*V, V + P, V - P
            # P can be a number (int or float), parameter set (P) or list[int |
            # float]
            # for multiplication P comes before variable

            left, right = self.types(one, one_type, two, two_type)

            if not self.consistent:
                # internal operations are made to adhere to the consistent form
                # this is notified to avoid doing this operation
                # saves time and computational resources
                left, one_type, right, two_type, add, sub, mul, div = (
                    self.make_consistent(
                        left,
                        one_type,
                        right,
                        two_type,
                        add,
                        sub,
                        mul,
                        div,
                    )
                )

            # now that the function is consistent
            # set one and two

            self.one = self._snapshot_operand(left(), self.one_type)
            self.two = self._snapshot_operand(right(), self.two_type)

            # check the mismatch
            # and rectify it if necessary
            # all iterations in the function will be done using _one and _two
            self.handle_mismatch()

            # fix the relational attributes
            self.handle_rel(mul, add, sub, div)

            if not self.index:
                # update the index
                self.handle_index()

            self.make_args()

            # self.give_name()

            self._build_rows()
        else:
            # if an empty function is created, attributes still need to be set
            # empty functions are used when doing operations outside
            # is more efficient computationally
            # this is especially true when the final structure is known
            # sum(variable_{i}) for example, where
            # instead of adding the function recursively, the final structure
            # can be passed

            self.mis = 0
            self._one = []
            self._two = []
            self.one = one
            self.two = two
            self.index = None

            self.handle_rel(mul, add, sub, div, ignore=True)
            self.one_type = one_type
            self.two_type = two_type
            self.make_args()
            self._initialize_empty_rows()

        self.give_name()

    def _capture_reduction(self, one: FunctionNode, two: V) -> None:
        """Capture legacy reduction operands without flattening their axes."""
        self.mis = 0
        self._one, self._two = one._, two._
        self.one, self.two = one, two
        one_index, two_index = one.index, two.index
        # Custom left addition and its original exceptions remain observable.
        self.index = (
            (*one_index, two_index)
            if type(one_index) is tuple
            else add_operands(one_index, (two_index,))
        )

    def _initialize_evaluation(self) -> None:
        """Initialize result storage, calculated variable and category."""
        self.X: dict[int, Number] = {}
        self.calculation: V | None = None
        self.category: str = ""
        self._matrix: dict = {}

    def _initialize_empty_rows(self) -> None:
        """Give empty and reduction shells independent row storage."""
        self._ = []
        self.n = 0
        self.name, self.pname = "", ""
        self.A, self.P, self.Y, self.Z, self.B, self.F = ([] for _ in range(6))
        self.variables = []

    @staticmethod
    def _snapshot_operand(
        operand: SymbolicOperand, kind: Elem | None
    ) -> SymbolicOperand:
        """
        Freeze variable membership while sharing its existing scalar members.
        """
        if kind == Elem.V and cast("V", operand).make_copy:
            return cast("V", operand).copy()
        return operand

    def _build_rows(self):
        """
        Compile a collection once; scalar construction only collects columns.
        """
        if self.parent is None:
            self._one_map = self._aligned_row_keys(
                self.one,
                self._one,
                self._one_map,
            )
            self._two_map = self._aligned_row_keys(
                self.two,
                self._two,
                self._two_map,
            )
            self.generate_matrices()
            self.birth_functions()
            # Newly birthed children have flat column IDs, unlike this root.
            self.P = [
                cast("list[int | None]", f.P) for f in self._ if f is not None
            ]
        else:
            self.update_variables()

    @staticmethod
    def _aligned_row_keys(operand, values, keys: Collection) -> Collection:
        """Retain repeated expression keys when a dictionary collapses them.

        Compiled selections keep their output coordinates separately. Other F
        collections retain composite coordinates on each scalar row. Expand
        these occurrences using the same consecutive-repeat rule as values.
        Ordinary one-to-one maps retain their existing representation.
        """
        if len(keys) == len(values) or not isinstance(operand, F):
            return keys
        layout = operand.__dict__.get("_row_layout")
        occurrences = (
            [(key,) for key in layout[1]]
            if layout is not None
            else [cast("F", row).index for row in operand]
        )
        repeat = len(values) // len(occurrences)
        return [key for key in occurrences for _ in range(repeat)]

    def types(
        self,
        one: FunctionNode | FunctionInput | None,
        one_type: Elem | None,
        two: FunctionNode | FunctionInput | None,
        two_type: Elem | None,
    ) -> tuple[SymbolicOperand, SymbolicOperand]:
        """
        Sets whether there is an element of a particular type in one and two

        :param one: First element
        :param one_type: Type of V | P | T | F
        :param two: Second element
        :param two_type: Type of V | P | T | F

        :return: Updated elements
        :rtype: tuple[V | P | T | F, V | P | T | F]
        """
        # this is meant to be avoided as far as possible
        # look at how the operations for each element is defined
        # to some extent it is difficult to avoid some sort of instance check
        # but if there is an instance check happening prior to the operation
        # it is better to pass the type directly
        # every instance check is time consumed, so at the least
        # avoid multiple instance checks for the same element

        def check_type(elem: object) -> Elem | None:
            """Identify symbolic operands; retain None for unknown types."""
            from .parameter import P
            from .theta import T
            from .variable import V

            if isinstance(elem, V):
                return Elem.V
            if isinstance(elem, P):
                return Elem.P
            if isinstance(elem, T):
                return Elem.T
            if isinstance(elem, F):
                return Elem.F
            return None

        if not one_type:
            # If one type is not known
            # perform instance check
            one = self._coerce_addend(one)
            one_type = check_type(one)

        if not two_type:
            two = self._coerce_addend(two)
            two_type = check_type(two)

        self.one_type = one_type
        self.two_type = two_type
        if one_type is None or two_type is None:
            message = "Arithmetic requires numeric or Gana operands"
            raise TypeError(message)

        # Inferred tags follow coercion; explicit tags are the caller's
        # contract. Keep the historical errors for incorrectly supplied tags.
        return cast("SymbolicOperand", one), cast("SymbolicOperand", two)

    def make_consistent(
        self,
        one: SymbolicOperand,
        one_type: Elem | None,
        two: SymbolicOperand,
        two_type: Elem | None,
        add: bool,
        sub: bool,
        mul: bool,
        div: bool,
    ) -> tuple[
        SymbolicOperand,
        Elem | None,
        SymbolicOperand,
        Elem | None,
        bool,
        bool,
        bool,
        bool,
    ]:
        """Normalize operands and keep their resolved type labels aligned.

        The constructor has already resolved omitted type hints with ``types``.
        Addition keeps numeric/theta operands on the right; multiplication
        keeps coefficients on the left. Subtraction and division transform
        an operand, so infer its new type: negating a V produces an F, while
        negating a negative-variable F can produce a V again. Theta subtraction
        retains its operand because direct T negation creates a new interval.
        """
        self.isconsistent = True
        one_type, two_type = self.one_type, self.two_type
        if (add and one_type in (Elem.P, Elem.T)) or (
            mul and two_type == Elem.P
        ):
            one, two = two, one
            self.one_type, self.two_type = two_type, one_type
        elif sub and one_type in (Elem.P, Elem.T) and two_type != Elem.T:
            one, two = self._coerce_addend(-two), one
            add, sub = True, False
            self.types(one, None, two, one_type)
        elif div and two_type == Elem.P:
            # The resolved Elem.P tag identifies a numerical parameter.
            one, two = self._coerce_addend(1 / cast("P", two)), one
            div, mul = False, True
            self.types(one, None, two, one_type)
        return one, self.one_type, two, self.two_type, add, sub, mul, div

    def handle_mismatch(self) -> None:
        """Align collection rows or retain a scalar member's operand maps.

        Root collections repeat shorter operands consecutively. Parented rows
        and false-valued operands retain singleton wrapping and their original
        maps. An unchanged collection keeps its values and map by identity.
        """
        if self.parent is None and self.one and self.two:
            # Root operands have been coerced; only scalar rows store numbers.
            self._align_collection_operands(
                cast("SymbolicOperand", self.one),
                cast("SymbolicOperand", self.two),
            )
        else:
            self.mis = 0
            self._one, self._two = [self.one], [self.two]
            self._one_map = self._scalar_operand_map(self.one, self.two)
            self._two_map = self._scalar_operand_map(self.two, self.one)

    def _align_collection_operands(
        self,
        one: SymbolicOperand,
        two: SymbolicOperand,
    ) -> None:
        """Validate divisibility before changing state, then align row counts.

        The caller has already excluded None and empty root operands.
        Negative mismatch means the left collection is longer; positive means
        the right is longer. Keep the established int(length / length) ratio
        calculation and error text, including operand/index representations.
        """
        lone, ltwo = len(one), len(two)
        if lone % ltwo != 0 and ltwo % lone != 0:
            message = (
                f"{one} with index {one.index} (length = {lone}) and "
                f"{two} with {two.index} (length = {ltwo}) "
                "are not compatible"
            )
            raise ValueError(message)
        if lone > ltwo:
            self.mis = -int(lone / ltwo)
            self._one, self._one_map = one._, one.map
            self._two = self._repeat_members(two._, -self.mis)
            self._two_map = self._repeat_members(two.map, -self.mis)
        elif ltwo > lone:
            self.mis = int(ltwo / lone)
            self._one = self._repeat_members(one._, self.mis)
            self._one_map = self._repeat_members(one.map, self.mis)
            self._two, self._two_map = two._, two.map
        else:
            self.mis = 0
            self._one, self._one_map = one._, one.map
            self._two, self._two_map = two._, two.map

    @staticmethod
    def _repeat_members[Member](
        members: Iterable[Member],
        count: int,
    ) -> list[Member]:
        """Repeat each member consecutively, retaining its original identity.

        Values and map keys use this same operation independently. Callers
        assign each result in the original order, including if iteration fails.
        Mapping iteration retains key insertion order without reindexing.
        """
        return [member for member in members for _ in range(count)]

    @staticmethod
    def _scalar_operand_map(
        operand: StoredOperand,
        other: StoredOperand,
    ) -> Collection:
        """Numeric and None members borrow the opposite symbolic operand map.

        Bool retains its existing int behavior. Empty symbolic collections keep
        their own maps; truth testing here would incorrectly borrow another.
        """
        if isinstance(operand, (int, float)) or operand is None:
            # A numeric/absent scalar borrows its paired symbolic operand.
            return cast("SymbolicOperand", other).map
        return operand.map

    def handle_index(self):
        r"""
        Handles (compounds if needed) the index
        Irrespective of the operation being done

        The index of a function is index.one + index.two
        Not in the mathematical sense!
        i am just using the __add__ dunder for I to create
        a function index basically.
        This is of the form

        .. math::

            f(\mathbf{x}, \mathbf{y})_{i,j} = \mathbf{x}_{i} + \mathbf{y}_{j}

        sets ``self.index``
        """

        # index is a combination of one and two
        index: list[object] = []
        # Called during root normalization, before scalar operands are stored.
        one = cast("SymbolicOperand", self.one)
        two = cast("SymbolicOperand", self.two)

        # update the index
        if self.one_type == Elem.F:
            index += cast("tuple[object, ...]", one.index)
        else:
            # elif self.one_type in [Elem.V, Elem.T, Elem.P]:

            index += (one.index,)

        if self.two_type == Elem.F:
            index += cast("tuple[object, ...]", two.index)
        else:
            # if self.two_type in [Elem.V, Elem.T, Elem.P]:
            index += (two.index,)

        self.index = tuple(index)

    def handle_rel(
        self,
        mul: bool,
        add: bool,
        sub: bool,
        div: bool,
        ignore: bool = False,
    ):
        """Set relation metadata after enforcing the affine compiler's domain.

        The internal reduction sentinel bypasses this check. Arithmetic
        requires a numeric left multiplier; numeric division has already
        been normalized into reciprocal multiplication.
        """
        if not ignore:
            self._validate_affine_relation(mul, div)
        self.mul, self.add, self.sub, self.div = mul, add, sub, div
        for enabled, symbol in (
            (mul, "\N{MULTIPLICATION SIGN}"),
            (add, "+"),
            (sub, "-"),
            (div, "÷"),
        ):
            if enabled:
                self.rel = symbol
                return
        if not ignore:
            _error_message = "one of mul, add, sub or div must be True"
            raise ValueError(_error_message)

    @staticmethod
    def _nonlinear_error():
        """Reject expressions outside the affine matrix representation."""
        message = (
            "Nonlinear operations are not supported; use numeric coefficients"
        )
        raise ValueError(message)

    def _validate_affine_relation(self, mul, div):
        """Reject symbolic products and unnormalized matrix division."""
        if div or (mul and self.one_type != Elem.P):
            self._nonlinear_error()

    def make_args(self):
        """
        Makes the arguments for the function
        This is convenient for passing to the birther functions
        and while making calls to the function.
        Also sets self.args
        """
        # these are passed on for mutation or birthing
        self.args = {
            "one_type": self.one_type,
            "two_type": self.two_type,
            "mul": self.mul,
            "add": self.add,
            "sub": self.sub,
            "div": self.div,
            "consistent": self.consistent,
            "case": self.case,
        }

    @staticmethod
    def _aligned_operand(operand, kind, index, source=None):
        """Reuse numeric values, thetas and aligned scalar expressions.

        ``handle_mismatch`` aligns F rows before child creation.
        Selecting those rows again interprets nested operand keys as domains
        and can require parent-only maps. Variables retain their existing
        coordinate-selection behavior, including shifted indices.
        """
        if kind == Elem.T and isinstance(operand, tuple):
            # Keep ownership without allocating a full selection per row.
            return source._row_reference(index)
        if kind in (Elem.P, Elem.T, Elem.F):
            return operand
        return operand(*index)

    def _remaining_row(self, operand, index, position):
        """Represent a surviving variable as a scalar F with flat columns.

        Shifted boundaries must neither edit the variable's coordinate map nor
        hand a vector-shaped variable wrapper to a scalar constraint row.
        """
        if self.one_type != Elem.V:
            return operand()
        row = operand.make_function()[0]
        row.parent, row.pos, row.index = self, position, index
        row.map = {index: row}
        self._inherit_compiled_row(row, position)
        return row

    def birth_functions(self):
        """Create scalar children from aligned operands and compiled rows.

        Preserve composite map keys for display and indexing, while reusing
        scalar F operands directly so nested rows keep their original columns.
        """

        one_keys, two_keys = list(self._one_map), list(self._two_map)
        one_function = self.one_type == Elem.F
        two_function = self.two_type == Elem.F
        template = self._scalar_template()
        for position in range(min(len(self._one), len(self._two))):
            one, two = self._one[position], self._two[position]
            one_key, two_key = one_keys[position], two_keys[position]
            # F keys already contain composite coordinates. Ordinary operands
            # contribute one coordinate; build tuples without a staging list.
            left = tuple(one_key) if one_function else (one_key,)
            if two is None:
                row = (
                    None
                    if isinstance(one, (int, float))
                    else self._remaining_row(one, left, position)
                )
                key = left
            else:
                right = tuple(two_key) if two_function else (two_key,)
                key = left + right
                row = self._new_aligned_row(
                    template,
                    one,
                    two,
                    one_key,
                    two_key,
                    index=key,
                    position=position,
                )
            self.map[key] = row
            self._.append(row)

    def _scalar_template(self):
        """Prepare invariant scalar metadata once per normalized collection.

        Child construction replaces mutable defaults before exposing a row.
        Keep the empty constructor's argument metadata for compatibility;
        relation and ownership fields match the validated parent collection.
        """
        template = F().__dict__
        template.update(
            parent=self,
            one_type=self.one_type,
            two_type=self.two_type,
            mul=self.mul,
            add=self.add,
            sub=self.sub,
            div=self.div,
            rel=self.rel,
            consistent=self.consistent,
            case=self.case,
            issumhow=self.issumhow,
        )
        return template

    def _new_aligned_row(
        self,
        template,
        one,
        two,
        one_idx,
        two_idx,
        *,
        index,
        position,
    ):
        """Build a public scalar from compiled data and empty-row metadata.

        Copy only invariant defaults from the per-collection template. Every
        mutable field is either fresh here or replaced by the row builders;
        only compiled A and theta terms deliberately share parent storage.
        Avoid running constructor dispatch, validation and empty formatting
        for every scalar of an already validated collection.
        """
        row = object.__new__(F)
        row.__dict__ = template.copy()
        row.__dict__.update(
            map={},
            X={},
            _matrix={},
            _one=[],
            _two=[],
            args=template["args"].copy(),
            Y=[],
            Z=[],
            F=[],
            index=index,
            pos=position,
        )
        if one:
            row.one = self._aligned_operand(
                one,
                self.one_type,
                one_idx,
                self.one,
            )
        row.two = self._aligned_operand(two, self.two_type, two_idx, self.two)
        row.update_variables()
        row.give_name()
        row.map[one_idx, two_idx] = row
        self._inherit_compiled_row(row, position)
        row._ = [row]
        return row

    def _inherit_compiled_row(self, child, position):
        """
        Share a compiled scalar row's values and symbolic owner references.
        """
        child.A = self.A[position]
        child.B = cast("list[Number]", self.B)[position]
        child._theta_terms = (
            self._theta_rows[position] if self._theta_rows else ()
        )
        child.rhs_thetas = self.rhs_thetas

    def update_variables(self):
        """Updates the variables in the function"""
        self.variables = []

        if self.one_type == Elem.F:
            # if function, extend the lists
            self.variables.extend(cast("F", self.one).variables)
        elif self.one_type == Elem.V:
            # if variable, append the variable
            self.variables.append(cast("V", self.one))

        if self.two_type == Elem.F:
            self.variables.extend(cast("F", self.two).variables)

        elif self.two_type == Elem.V:
            self.variables.append(cast("V", self.two))

        # make a matrix of positions of the variables
        self.P = [v.n for v in self.variables if v is not None]

    def give_name(self):
        """Gives a name to the function"""

        # set by program
        self.pname = ""

        if self.case == FCase.SUM:
            variable, over, _ = cast("ReductionInfo", self.issumhow)

            self.name = f"sigma({variable}({variable.index}),{over})"
        # elif self.case == FCase.NEGSUM:
        # self.name =
        # f'-sigma({self.variables[0].parent}[{self.variables[0].pos}:{self.variables[-1].pos}])'
        else:
            one = "" if self.one is None else str(self.one)
            two = "" if self.two is None else str(self.two)
            self.name = self._join_display(one, two)

    def _join_display(self, one, two):
        """Join displayed operands, retaining readable signs on theta terms."""
        if not two:
            return one
        signed = self._signed_theta_display(one, two)
        return signed if signed is not None else f"{one}{self.rel}{two}"

    def _signed_theta_display(self, one, two):
        """Absorb a negative theta label into an additive display operator."""
        if self.two_type == Elem.T and two.startswith("-"):
            if self.add:
                return f"{one} - {two[1:]}"
            if self.sub:
                return f"{one} + {two[1:]}"
        return None

    def categorize(self, category: str):
        """Categorizes the function

        :param category: Category name
        :type category: str
        """
        self.category = category
        for c in self._:
            # Categorization requires populated rows; holes still fail.
            cast("F", c).category = category

    @property
    def struct(self) -> tuple[Elem | None, Elem | None]:
        """Structure of the function"""
        return (self.one_type, self.two_type)

    @property
    def elements(self) -> list[T | ParameterSet | V]:
        """Elements in the function"""
        return (
            self.variables
            + self.mul_parameters
            + self.rhs_parameters
            + self.rhs_thetas
        )

    @property
    def index_flat(self) -> list[tuple[I, ...] | set[tuple[I, ...]]]:
        """Flattens the index of the function"""
        return (
            [v.index for v in self.variables]
            + [p.index for p in self.mul_parameters]
            + [r.index for r in self.rhs_parameters]
            + [t.index for t in self.rhs_thetas]
        )

    # endregion

    # region Indexing and selection

    def __call__(self, *key) -> FunctionNode:
        """Select existing compiled rows without rebuilding operand trees."""
        if not key or key == self.index:
            return self
        from .rows import select_expression

        return select_expression(self, key)

    def __getitem__(self, pos: int) -> FunctionNode | None:
        """Return a stored row, including a shifted-boundary placeholder."""
        return self._[pos]

    def __iter__(self) -> Iterator[FunctionNode | None]:
        """
        Iterate rows and missing-row placeholders in their stored order.
        """
        return iter(self._)

    def __len__(self):
        return len(self._)

    # endregion

    # region Unary operations

    def __neg__(self):
        """Negate affine rows and infer operand types after simplification.

        Negating a negated variable returns a V, so retaining its earlier F
        type would corrupt double negation. Compact sums use row scaling to
        avoid traversing the reduction's self-link. Scalar children store
        numeric operands directly; wrap those before constructing a new F.
        """
        if self.case == FCase.NEGVAR:
            return self.two
        if (
            self.rhs_thetas
            or self.case == FCase.SUM
            or hasattr(self, "_row_layout")
        ):
            return self * -1
        return F(
            one=self._coerce_addend(
                -cast("SymbolicOperand | Number", self.one)
            ),
            two=self._coerce_addend(self.two),
            add=self.sub,
            sub=self.add,
            mul=self.mul,
            div=self.div,
        )

    def __pos__(self):
        return self

    # endregion

    # region Arithmetic helpers

    def _coerce_addend(self, other):
        """Wrap numeric operands without interpreting term indices as rows.

        A scalar has one dummy coordinate and is broadcast by handle_mismatch.
        A tuple retains the public theta-bound convention.
        """
        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            return make_P(other, index=(I(size=1, dummy=True),))
        if isinstance(other, tuple):
            return make_T(other, index=(I(size=len(self), dummy=True),))
        if isinstance(other, list):
            if other and isinstance(other[0], tuple):
                return make_T(other)
            return make_P(other)
        return other

    def _additive(self, other, subtract=False):
        """
        Construct ordinary arithmetic even when an operand is a reduction.
        """
        if other is None:
            return self
        if isinstance(other, (int, float)) and other == 0:
            return self
        return F(
            one=self,
            two=self._coerce_addend(other),
            add=not subtract,
            sub=subtract,
            one_type=Elem.F,
        )

    def _scale_by(self, parameter):
        """Distribute compatible multipliers and broadcast other row counts.

        Distribution preserves the existing expanded expression display. A
        reduction or a different-size multiplier is compiled directly from its
        aligned rows; distributing those would change the broadcast ordering.
        Theta terms also use compiled rows: distributing into T would invoke
        its interval transformation instead of scaling coefficients.
        """
        if self.rhs_thetas:
            return F(one=parameter, mul=True, two=self)
        if (
            self.case == FCase.SUM
            or self.parent is not None
            or hasattr(self, "_row_layout")
            or len(parameter) != len(self)
        ):
            return F(one=parameter, mul=True, two=self)
        if self.mul:
            return F(one=parameter * self.one, mul=True, two=self.two)
        if self.div:
            return F(one=parameter * self.one, div=True, two=self.two)
        return F(
            one=parameter * self.one,
            two=parameter * self.two,
            add=self.add,
            sub=self.sub,
        )

    # endregion

    # region Binary arithmetic

    def __add__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self:
        """Add aligned rows, preserving both operands' affine constants."""
        return self._additive(other)

    def __radd__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self:
        return self + other

    def __sub__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self:
        """
        Subtract aligned rows, negating coefficients and constants together.
        """
        return self._additive(other, subtract=True)

    def __rsub__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> Self:
        return -self + other

    def __mul__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> FunctionNode | int | None:
        """Scale affine coefficients and constants with a numerical operand."""
        from .parameter import P

        other = normalize_operand(other)
        if other is None:
            return None
        if isinstance(other, (int, float)):
            if other == 0:
                return 0
            if other == 1:
                return self
            other = make_P(other, index=(I(size=len(self), dummy=True),))
        elif isinstance(other, list) and all(
            isinstance(x, (int, float)) for x in other
        ):
            # The all() guard excludes the tuple alternative in NumericList.
            other = make_P(cast("list[Number]", other))
        if not isinstance(other, P):
            message = (
                f"{self}*{other}: "
                "Multiplication requires a numerical parameter."
            )
            raise NotImplementedError(message)
        return self._scale_by(other)

    def __rmul__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> FunctionNode | int | None:
        """Delegate scaling, including the zero and None identity results."""
        return self * other

    def __truediv__(
        self, other: Self | ArithmeticOperand | None
    ) -> FunctionNode | int | None:
        """Scale affine rows by reciprocals, including numeric lists."""
        other = normalize_operand(other)
        if isinstance(other, list):
            values = [
                value for value in other if isinstance(value, (int, float))
            ]
            if not values or len(values) != len(other):
                message = "Division requires a nonempty numeric list"
                raise TypeError(message)
            other = make_P(values)
        # Valid reciprocals are numerical/P operands. Unsupported public inputs
        # retain Python's original operator TypeError rather than a new guard.
        return self * (1 / cast("Number | P", other))

    # endregion

    # region Comparisons

    def __ne__(self, other):
        """Reject disequality instead of inverting a truthy constraint."""
        reject_disequality()

    def __eq__(self, other: object):
        """Build equality using arithmetic's existing operand validation."""
        return C(self - cast("F | ArithmeticOperand | None", other))

    def __lt__(self, other: Self | ExpressionSet):
        return self <= other

    def __le__(self, other: Self | ExpressionSet):

        return C(self - other, leq=True)

    def __gt__(self, other: Self | ExpressionSet):
        return self >= other

    def __ge__(self, other: Self | ExpressionSet):
        return C(-self + other, leq=True)

    # endregion

    # region Matrix compilation

    @staticmethod
    def _matrix_values(values, kind):
        """Skip scalar wrappers when compilation needs only symbol presence.

        Native SymbolValues contain no missing members: their V coefficients
        are one and their T terms use the separately aligned coordinate keys.
        Lists and shifted/gapped facades retain their actual values so None
        boundaries and numeric/F payloads keep their existing semantics.
        """
        if kind in (Elem.V, Elem.T):
            facade = import_module("gana.storage.symbols").SymbolValues
            if isinstance(values, facade):
                return repeat(True, len(values))
        return values

    @staticmethod
    def _operand_theta_terms(operand, kind, value, key):
        """
        Read symbolic terms without copying bounds or allocating theta IDs.
        """
        if kind == Elem.F and value is not None:
            return value._theta_terms
        if kind == Elem.T and value is not None:
            return [(operand._owner_root, key, -1)]
        return ()

    def _compile_theta_terms(self):
        """Propagate signed RHS terms through aligned affine operations."""
        if not self.rhs_thetas:
            self._theta_rows = ()
            return
        rows: list[list[ThetaTerm]] = []
        for one, two, key_one, key_two in zip(
            self._matrix_values(self._one, self.one_type),
            self._matrix_values(self._two, self.two_type),
            self._one_map,
            self._two_map,
        ):
            left = self._operand_theta_terms(
                self.one,
                self.one_type,
                one,
                key_one,
            )
            right = self._operand_theta_terms(
                self.two,
                self.two_type,
                two,
                key_two,
            )
            scale = one if self.mul else (-1 if self.sub else 1)
            terms = [
                *left,
                *((owner, key, scale * a) for owner, key, a in right),
            ]
            rows.append(terms)
        self._theta_rows = rows

    @staticmethod
    def _affine_row(value, kind):
        """Read one aligned operand as coefficients and a negated constant.

        ``B`` is the right-hand-side constant, so a numeric operand contributes
        its negative. Reduction rows start with an empty B and mean zero.
        Theta terms are registered separately by the owning program.
        """
        if value is None:
            return [], 0
        if kind == Elem.F:
            return value.A, value.B or 0
        if kind == Elem.V:
            return [1], 0
        if kind == Elem.P:
            return [], -value
        return [], 0

    def _combine_row(self, one, two):
        """Combine already aligned scalar rows without re-expanding indices."""
        left, lhs_constant = self._affine_row(one, self.one_type)
        right, rhs_constant = self._affine_row(two, self.two_type)
        if self.mul:
            # The consistent affine form places the numerical multiplier first.
            return [one * a for a in right], one * rhs_constant
        sign = -1 if self.sub else 1
        return left + [
            sign * a for a in right
        ], lhs_constant + sign * rhs_constant

    def _matrix_operands(self):
        """
        Keep operand metadata needed for selection and theta registration.
        """
        self.variables = []
        self.rhs_parameters = []
        self.mul_parameters = []
        self.rhs_thetas = []
        for operand, kind in (
            (self.one, self.one_type),
            (self.two, self.two_type),
        ):
            if kind == Elem.F:
                self.variables.extend(cast("F", operand).variables)
                self.rhs_thetas.extend(getattr(operand, "rhs_thetas", ()))
            elif kind == Elem.V:
                self.variables.append(cast("V", operand))
            elif kind == Elem.T:
                self.rhs_thetas.append(cast("T", operand)._owner_root)
        if self.one_type == Elem.P:
            self.mul_parameters.append(cast("P", self.one))
        if self.two_type == Elem.P:
            self.rhs_parameters.append(cast("P", self.two))
        self.rhs_thetas = list({id(t): t for t in self.rhs_thetas}.values())

    def generate_matrices(self):
        """Compile affine rows as ``A V = B + F theta``.

        Use the same repeated operand rows as ``birth_functions``. Constants
        from both operands must survive each operation; term coefficients stay
        aligned with variable occurrences until accumulation by column ID.
        """
        self._matrix_operands()
        self._compile_theta_terms()
        self.F, self.Z = [], []
        coefficients_by_row: list[list[Number]] = []
        self.A, self.B = coefficients_by_row, []
        for one, two in zip(
            self._matrix_values(self._one, self.one_type),
            self._matrix_values(self._two, self.two_type),
        ):
            coefficients, constant = self._combine_row(one, two)
            coefficients_by_row.append(coefficients)
            self.B.append(constant)

    @property
    def matrix(self) -> dict:
        """Matrix as dict

        Returns:
            dict: Dictionary mapping of positions to values in A matrix
        """
        if self._matrix:
            return self._matrix

        if self.parent is not None:
            # Several terms may name the same column, including cancellation.
            self._matrix = {}
            for column, coefficient in zip(self.P, self.A):
                self._matrix[column] = (
                    self._matrix.get(column, 0) + coefficient
                )
        else:
            self._matrix = {f: cast("F", f).matrix for f in self._}

        return self._matrix

    # endregion

    # region Solution and evaluation

    @staticmethod
    def _solution_identity(value, identity):
        """Substitute for an absent operand while preserving solved zeros."""
        return identity if value is None else value

    def _solution_value(self, n_sol):
        """
        Evaluate reductions and unary operands without recursive self-calls.

        Reduced variables require numeric solved values. Missing values keep
        the arithmetic TypeError instead of being silently omitted or zeroed.
        """
        match self.case:
            case FCase.SUM:
                return sum(cast("Number", v.X[n_sol]) for v in self.variables)
            case FCase.NEGSUM:
                return -sum(cast("Number", v.X[n_sol]) for v in self.variables)
            case FCase.NEGVAR:
                return -cast("Number", cast("V", self.two).X[n_sol])
            case FCase.FVAR:
                return cast("V", self.two).X[n_sol]
            case _:
                return self.solution(n_sol)

    @staticmethod
    def _solution_operand(elem, elem_type, n_sol):
        """
        Resolve a numeric, variable or expression operand at a solve index.
        """
        match elem_type:
            case Elem.P:
                return elem
            case Elem.V:
                return elem.X[n_sol]
            case Elem.F:
                return elem._solution_value(n_sol)
            case _:
                return None

    def solution(self, n_sol: int = 0) -> Number | list[Number]:
        """Evaluate the value of the function.

        :param n_sol: The solution number to evaluate, defaults to 0
        :type n_sol: int, optional

        :returns: Evaluated function value(s)
        :rtype: float | int | list[float | int]
        """

        # if this is a function container, evaluate all its children
        if self.parent is None:
            # if this is a function, set
            # do evaluations for all the children and return
            # Children of a root evaluate to scalars. Missing rows retain the
            # historical AttributeError instead of being silently skipped.
            return [
                cast("Number", cast("F", f).solution(n_sol)) for f in self._
            ]

        one = self._solution_operand(self.one, self.parent.one_type, n_sol)
        two = self._solution_operand(self.two, self.parent.two_type, n_sol)

        # arithmetic evaluation
        if self.mul:
            self.X[n_sol] = self._solution_identity(
                one,
                1,
            ) * self._solution_identity(two, 1)
        elif self.div:
            self.X[n_sol] = one / two
        elif self.add:
            self.X[n_sol] = self._solution_identity(
                one,
                0,
            ) + self._solution_identity(two, 0)
        elif self.sub:
            self.X[n_sol] = self._solution_identity(
                one,
                0,
            ) - self._solution_identity(two, 0)

        return self.X[n_sol]

    @overload
    def eval(self, *values: Number) -> Number:
        """Evaluate one scalar row using positional numeric values."""
        ...

    @overload
    def eval(self, values: Sequence[Sequence[Number]], /) -> list[Number]:
        """Evaluate a collection with one sequence of per-row values."""
        ...

    def eval(
        self, *values: Number | Sequence[Sequence[Number]]
    ) -> Number | list[Number]:
        """Evaluate the function for given parameter values.

        :param values: Values for variables in the order they feature in the
            function
        :type values: float | int | Sequence[Sequence[float | int]]

        :returns: Evaluated function value(s)
        :rtype: float | int | list[float | int]
        """
        if self.parent:
            coefficients = cast("list[Number]", self.A)
            scalars = cast("tuple[Number, ...]", values)
            return sum(a * v for a, v in zip(coefficients, scalars))
        _sol = []
        # The collection overload takes one vector of argument rows; preserve
        # zip/unpacking errors for other arities rather than reshaping values.
        vectors = cast("tuple[Sequence[Sequence[Number]], ...]", values)
        pairs = cast(
            "Iterable[tuple[F, Sequence[Number]]]", zip(self._, *vectors)
        )
        for f, v in pairs:
            _sol.append(f.eval(*v))
        return _sol

    # endregion

    # region Display and representation

    @cached_property
    def longname(self):
        """Gives a longer more descriptive name for the function"""
        one = self._long_operand(self.one)
        two = self._long_operand(self.two)
        return self._join_display(one, two)

    @staticmethod
    def _long_operand(value):
        """Render numbers or symbols without assuming a long name exists."""
        if value is None:
            return ""
        return (
            str(value) if isinstance(value, (int, float)) else value.longname
        )

    @staticmethod
    def _latex_operand(value):
        """Render a captured numeric value or a symbolic operand."""
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        return value.latex()

    @staticmethod
    def _latex_sum_index(index, position, reduced):
        """Render one variable axis, replacing the reduced axis by i."""
        if position == reduced:
            return "i"
        if isinstance(index, list):
            return index[0].ltx
        return index.ltx.replace("[", "").replace("]", "")

    def _latex_sum(self):
        """
        Render whole or indexed reductions without assuming a single axis.
        """
        variable, over, position = cast("ReductionInfo", self.issumhow)
        axes = (
            over
            if isinstance(over, tuple)
            else (() if over is None else (over,))
        )
        domain = r" \times ".join(axis.ltx for axis in axes)
        prefix = rf"\sum_{{i \in {domain}}}" if domain else r"\sum"
        if isinstance(variable, F):
            body = rf"\left({variable.latex()}\right)"
        else:
            index = ", ".join(
                self._latex_sum_index(axis, n, position)
                for n, axis in enumerate(variable.index)
            )
            body = rf"{variable.ltx or variable.name}_{{{index}}}"
        sign = "-" if self.case == FCase.NEGSUM else ""
        return rf"{sign}{prefix} {body}"

    def _latex_calculation(self):
        """
        Render calculated-variable bindings without mutating expression state.
        """
        # CALC rendering is selected only for a bound calculated variable.
        calculation = cast("V", self.calculation)
        if calculation.case == FCase.SUM:
            body = self._latex_sum()
        else:
            two = cast("SymbolicOperand", self.two)
            body = rf"{self._latex_operand(self.one)} \cdot {two.latex()}"
        return rf"{calculation.latex()} = {body}"

    def _latex_subtraction(self, one, two):
        """
        Bracket composite right-hand terms so subtraction remains unambiguous.
        """
        compound = (
            self.two_type == Elem.F
            and cast("F", self.two).struct != (Elem.P, Elem.V)
            and cast("F", self.two).case != FCase.SUM
        )
        if compound:
            two = f"({two})"
            if self.one_type == Elem.F and cast("F", self.one).struct != (
                Elem.P,
                Elem.V,
            ):
                one = f"({one})"
        return rf"{one} - {two}"

    def _latex_product(self, one, two):
        """
        Bracket affine factors and retain the compact negative-variable form.
        """
        if self.case == FCase.NEGVAR:
            return rf"-{two}"
        if self.one_type == Elem.F:
            one = f"({one})"
        if self.two_type == Elem.F:
            two = f"({two})"
        return rf"{one} \cdot {two}"

    def _latex_relation(self, one, two):
        """Join rendered operands using the selected affine operation."""
        signed = self._signed_theta_display(one, two)
        if signed is not None:
            return signed
        if self.add:
            return rf"{one} + {two}"
        if self.sub:
            return self._latex_subtraction(one, two)
        if self.mul:
            return self._latex_product(one or "0", two)
        if self.div:
            return rf"\frac{{{one}}}{{{two}}}"
        return one

    def latex(self) -> str:
        """
        Render affine operations and reductions with their mathematical order.
        """
        if self.case == FCase.CALC:
            return self._latex_calculation()
        if self.case == FCase.FVAR:
            return cast("V", self.two).latex()
        if self.case in (FCase.SUM, FCase.NEGSUM):
            return self._latex_sum()
        one = self._latex_operand(self.one)
        two = self._latex_operand(self.two)
        if self.two is None:
            return one
        return self._latex_relation(one, two)

    def show(self, descriptive: bool = False):
        """
        Display the function

        :param descriptive: Whether to show all birthed functions, defaults to
            False
        :type descriptive: bool, optional
        """
        if descriptive:
            for f in self._:
                f = cast("F", f)
                display(Math(rf"[{f.n}]" + r"\text{   }" + f.latex()))
        else:
            display(Math(rf"[{self.n}]" + r"\text{   }" + self.latex()))

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
