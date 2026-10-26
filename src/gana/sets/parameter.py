"""Paramter Set"""

from __future__ import annotations

import logging
import operator
import weakref
from itertools import product
from typing import TYPE_CHECKING, Self, Union
from warnings import warn

from gana.types import Number, NumericList, NumericTuple

from ..indexing.staging import CartesianMap, fill_map
from ..storage import parameters as storage
from ..utils.draw import draw
from ._element import _E
from .birth import make_T
from .cases import PCase
from .function import F
from .index import I
from .operands import normalize_operand
from .variable import V

logger = logging.getLogger("gana")

if TYPE_CHECKING:
    from collections.abc import Callable

    from .theta import T

# Optional adapters below are disabled; retain their imports and availability
# checks alongside that commented implementation until the adapters return.
# try:
#     from pyomo.environ import Param as PyoParam
#
#     has_pyomo = True
# except ImportError:
#     has_pyomo = False
#
# try:
#     from sympy import Idx, IndexedBase, symbols
#
#     has_sympy = True
# except ImportError:
#     has_sympy = False

# Preserve original union members; keep Self at use sites.
# Forward references preserve runtime introspection without circular imports.
type ArithmeticOperand = Union[
    "V",
    "T",
    "F",
    Number,
    NumericTuple,
    NumericList,
]
type ComparisonOperand = Union[
    "P",
    "T",
    "F",
    Number,
    NumericTuple,
    NumericList,
]


class P(_E[float]):
    """
    Ordered set of parameters.

    Does not support `inf` or `nan` values.

    :param index: Indices of the parameter set.
    :type index: tuple[I], optional
    :param _: List of parameters. All values are converted to float.
    :type _: list[int | float], optional
    :param mutable: If the parameter set is mutable.
    :type mutable: bool, optional
    :param tag: Tag/details
    :type tag: str, optional

    :ivar index: Index of the parameter set
    :vartype index: I
    :ivar _: List of parameters (converted to float)
    :vartype _: list[int | float]
    :ivar mutable: If the parameter set is mutable
    :vartype mutable: bool
    :ivar tag: Tag/details
    :vartype tag: str
    :ivar name: Name, set by the program
    :vartype name: str
    :ivar n: Number id, set by the program
    :vartype n: int
    :ivar map: Index to parameter mapping
    :vartype map: dict[X | Idx, Var]
    :ivar case: Special case of the parameter set
    :vartype case: PCase

    Comparisons defer unsupported operand types to Python reflection. Set
    comparisons reduce pairwise results with ``all``, including ``!=``.

    :raises ValueError: If the parameter values and the length of indices do
        not match
    """

    # TODO update Errors in docstring
    # TODO add examples

    _native_storage: storage.ParameterStorage
    _compact_staging = True

    # region Construction and validation

    def __setattr__(self, name, value):
        """
        Prevent replacement of native facades outside atomic program updates.
        """
        if name in ("_", "map") and "_native_storage" in self.__dict__:
            raise TypeError(storage._STRUCTURAL)
        object.__setattr__(self, name, value)

    def __setstate__(self, state):
        """Restore Python metadata and rebind a deserialized native payload."""
        self.__dict__.update(state)
        native = self.__dict__.get("_native_storage")
        if native is not None:
            native.root = weakref.ref(self)

    def __init__(
        self,
        *index: I,
        _: list[float] | float | None = None,
        mutable: bool = False,
        tag: str | None = "",
        ltx: str | None = "",
        name: str = "",
    ):
        """Prepare numeric storage completely before exposing mapped values."""
        _E.__init__(self, *index, tag=tag, ltx=ltx, mutable=mutable, name=name)
        self.case = PCase.SET
        self.n_splices = 1
        if _ is not None:
            self._initialize_values(_)

    def _initialize_values(self, values) -> None:
        """
        Normalize values and reject length mismatches before filling the map.
        """
        # Float conversion below already handles list members, including NumPy
        # scalars. Avoid scanning internally computed numeric lists twice.
        # Operand dispatch separately rejects empty/invalid arithmetic lists.
        if not isinstance(values, list):
            values = normalize_operand(values)
        if isinstance(values, (int, float)):
            self._implicit_index(1)
            self._ = [float(values)] * len(self.map)
            self._set_numeric_case(values)
        else:
            self._ = [float(value) for value in values]
            if not self.index and self._:
                self._implicit_index(len(self._))
                self.name = "φ"
        if len(self._) != len(self.map):
            message = "Parameter values length must match its coordinates"
            raise ValueError(message)
        fill_map(self.map, self._)

    def _set_numeric_case(self, value: float) -> None:
        """
        Keep constant naming and sign shortcuts consistent after scalar
        updates.
        """
        self.name = str(value)
        if value == 0:
            self.case = PCase.ZERO
        elif value < 0:
            self.case = PCase.NEGNUM
        else:
            self.case = PCase.NUM

    @staticmethod
    def _check_staged_value(mapped, value) -> None:
        """Accept numeric aligned values, including an identical NaN object."""
        if not isinstance(value, (int, float)):
            message = "Parameter values must be numeric"
            raise TypeError(message)
        if mapped is not value and mapped != value:
            message = "Parameter map and values disagree"
            raise ValueError(message)

    def _validated_values(self, *, collect: bool = True) -> dict:
        """Validate raw buffers and optionally collect a detached mutation map.

        Registration consumes the existing buffers immediately, so it needs
        validation without a second coordinate dictionary. Conversion still
        runs in that path to reject invalid numeric subclasses before binding.
        """
        if "_native_storage" in self.__dict__:
            # Both facades are views of one payload, including NaN values.
            return self.map.copy() if collect else {}
        if len(self._) != len(self.map):
            message = "Parameter values length must match its coordinates"
            raise ValueError(message)
        if not collect and self._validate_compact_values():
            return {}
        return self._validate_mapped_values(collect=collect)

    def _validate_compact_values(self) -> bool:
        """Validate raw buffers without keys or redundant float conversion.

        Exact floats can use equality without invoking subclass hooks.
        Identity admits an unchanged NaN; distinct NaNs still fail.
        Other inputs retain full validation and conversion on every attempt.
        """
        mapping = self.map
        if not isinstance(mapping, CartesianMap) or not mapping.compact:
            return False
        for mapped, value in zip(mapping.staged_values(), self._):
            if type(value) is float and (
                mapped is value or (type(mapped) is float and mapped == value)
            ):
                continue
            self._check_staged_value(mapped, value)
            float(value)
        return True

    def _validate_mapped_values(self, *, collect: bool) -> dict:
        """Check edited or irregular maps in their actual insertion order."""
        mapping = {}
        for (key, mapped), value in zip(self.map.items(), self._):
            self._check_staged_value(mapped, value)
            if key is not None:
                converted = float(value)
                if collect:
                    mapping[key] = converted
        return mapping

    # endregion

    # region Indexing and selection

    def __call__(self, *key: I) -> P:
        """
        Select numerical members, retaining skipped and missing-key behavior.

        New selections are P instances, including when called on a subclass.
        """
        if not key or self._unpack_index(key) == self._unpack_index(
            self.index,
        ):
            # if the index is an exact match
            # or no key is passed
            return self

        # the check helps to handle if a variable itself is an index
        # we do not want to iterate over the entire variable set
        # but treat the variable as a single index element
        key = self._normalize_index(key)

        # if a subset is passed,
        # first create a product to match
        # the indices

        # create a new variable set to return
        p = self._new_selection(P(**self.args), key)
        if not storage.select(self, p, key):
            self._populate_selection(p, product(*key))
        return p

    def _populate_selection(self, selected, coordinates) -> None:
        """Populate Python containers with the historical skip policy."""
        # should be able to map these
        for coordinate in coordinates:
            # this helps weed out any None indices
            # i.e. skips
            index = None if any(i is None for i in coordinate) else coordinate

            if index is None:
                parameter = None
            else:
                parameter = self.map[index]

            selected.map[index] = parameter
            selected._.append(parameter)

    # endregion

    # region Unary operations and conversion

    def __neg__(self):
        if self.case == PCase.ZERO:
            # if zero return self
            return self

        if self.case in [PCase.NUM, PCase.NEGNUM]:
            # if number return a negation

            return P(*self.index, _=-self._[-1])

        # else negate the number and return a new parameter set
        p = P(*self.index, _=[-i for i in self._], **self.args)
        if self.case == PCase.NEGSET:
            # if this is already a negated set
            # make it a normal set now
            p.name = f"{self.name[1:]}"  # remove the negative sign
            p.case = PCase.SET
        else:
            # if this is a normal set
            # make it a negated set
            p.case = PCase.NEGSET
            p.name = f"-{self}"  # add the negative sign
        # return the new parameter set
        return p

    def __pos__(self):
        """Preserve all values under unary plus."""
        return self

    def __abs__(self):
        """Take absolute values independently of the parameter case."""
        if self.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
            return P(
                *self.index,
                _=abs(self._[-1]),
                tag=self.tag,
                ltx=self.ltx,
                mutable=self.mutable,
            )
        p = P(
            *self.index,
            _=[abs(value) for value in self._],
            tag=self.tag,
            ltx=self.ltx,
            mutable=self.mutable,
        )
        p.name = f"|{self.name}|"
        return p

    def __float__(self):
        if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
            return self._[-1]
        return self

    # endregion

    # region Arithmetic helpers

    def _subtract_number(self, other):
        """
        Subtract a scalar while retaining numeric-parameter simplification.
        """
        if other == 0:
            return self
        if self.case in [PCase.NEGNUM, PCase.NUM]:
            value = self._[-1] - other
            return P(*self.index, _=value, **self.args) if value else 0
        p = P(*self.index, _=[i - other for i in self._], **self.args)
        p.name = f"({self}-{other})"
        return p

    def _subtract_list(self, other):
        """Keep the existing list broadcasting and mismatch warning policy."""
        if self.case in [PCase.NUM, PCase.NEGNUM]:
            values = [self._[-1] - i for i in other]
        else:
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} - {other}: "
                    f"len(self) ({len(self)}) != len(other) ({len(other)})",
                )
            values = [i - j for i, j in zip(self._, other)]
        p = P(*self.index, _=values, **self.args)
        p.name = f"({self}-φ)"
        return p

    def _subtract_parameter(self, other):
        """Subtract parameter values using the existing scalar/set rules."""
        if other.case == PCase.ZERO:
            return self
        if self.case in [PCase.NUM, PCase.NEGNUM]:
            if other.case in [PCase.NUM, PCase.NEGNUM]:
                return self._subtract_number(other._[-1])
            values = [self._[-1] - i for i in other._]
        elif other.case in [PCase.NUM, PCase.NEGNUM]:
            values = [i - other._[-1] for i in self._]
        else:
            if len(self) != len(other):
                message = (
                    f"Index mismatch {self} - {other}: "
                    f"len(self) ({len(self)}) != len(other) ({len(other)})"
                )
                raise ValueError(message)
            values = [i - j for i, j in zip(self._, other._)]
        p = P(*self.index, _=values, **self.args)
        p.name = f"({self}-{other})"
        return p

    @staticmethod
    def _numeric_payload(other):
        """Read a real scalar or nonempty numeric sequence without dispatch."""
        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            return [other], True, ()
        if isinstance(other, P):
            scalar = other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO)
            return other._, scalar, other.index
        if isinstance(other, list) and other:
            if all(isinstance(value, (int, float)) for value in other):
                return other, False, ()
        message = (
            "Arithmetic requires a numeric scalar, parameter, "
            "or nonempty numeric list"
        )
        raise TypeError(message)

    def _numeric_alignment(self, other):
        """Broadcast numeric constants; require equal lengths for two sets.

        An indexless scalar may adopt a vector operand's coordinates. Indexed
        operands retain their own coordinates and cannot be truncated.
        """
        right, right_scalar, right_index = self._numeric_payload(other)
        left_scalar = self.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO)
        if left_scalar and right_scalar:
            return [self._[-1]], [right[-1]], self.index, True
        size = len(right) if left_scalar else len(self)
        left = [self._[-1]] * size if left_scalar else self._
        right = [right[-1]] * size if right_scalar else right
        if len(left) != len(right):
            message = (
                "Numeric operand lengths must match unless one is a scalar"
            )
            raise ValueError(message)
        index = self.index
        if left_scalar and len(self) == 1 and size != 1:
            index = right_index
        return left, right, index, False

    def _numeric_operation(self, other, operation, symbol, reverse=False):
        """Evaluate numeric results before constructing a parameter."""
        left, right, index, scalar = self._numeric_alignment(other)
        if reverse:
            left, right = right, left
        values = [operation(a, b) for a, b in zip(left, right)]
        p = P(
            *index,
            _=values[0] if scalar else values,
            tag=self.tag,
            ltx=self.ltx,
            mutable=self.mutable,
        )
        if not scalar:
            label = "φ" if isinstance(other, list) else str(other)
            p.name = (
                f"{label}{symbol}{self}"
                if reverse
                else f"{self}{symbol}{label}"
            )
        return p

    def _divide_numeric(self, numerator: Number) -> P:
        """Divide numeric values, preserving coordinates and constant cases."""
        numeric = self.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO)
        values = (
            numerator / self._[-1]
            if numeric
            else [numerator / value for value in self._]
        )
        p = P(
            *self.index,
            _=values,
            tag=self.tag,
            ltx=self.ltx,
            mutable=self.mutable,
        )
        if not numeric:
            p.name = f"{numerator}/{self}"
        return p

    # endregion

    # region Binary arithmetic

    # Handling basic operations----
    # if there is a zero on the left, just return P
    # if the other is a parameter, add the values
    # if the other is a function/variable, return a function

    # r<operation>
    # for the right hand side operations
    # they only kick in when the left hand side operator
    # does not have the operation/the operation did not work
    # in this case, we just do the equivalent self

    def __add__(self, other):
        """
        Add real values or defer symbolic addition to expression compilation.
        """
        other = normalize_operand(other)
        if other is None:
            return self
        if isinstance(other, (int, float, list, P)):
            result = self._numeric_operation(other, operator.add, "+")
            return 0 if result.case == PCase.ZERO else result
        if isinstance(other, tuple):
            other = make_T(other, index=self.index)
        return F(one=other, two=self, add=True)

    def __radd__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> P:
        # let __add__() handle the addition
        return self + other

    def __sub__(self, other):
        """
        Subtract real values or preserve the order of symbolic subtraction.
        """
        other = normalize_operand(other)
        if other is None:
            return self
        if isinstance(other, (int, float, list, P)):
            result = self._numeric_operation(other, operator.sub, "-")
            return 0 if result.case == PCase.ZERO else result
        if isinstance(other, tuple):
            other = make_T(other, index=self.index)
        return F(one=self, two=other, sub=True)

    def __rsub__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> P | F:
        # let negation and __add__ handle the subtraction
        return -self + other

    def __mul__(self, other):
        """Multiply numbers or delegate symbolic scaling to its operand."""
        other = normalize_operand(other)
        if other is None:
            return None
        if isinstance(other, (int, float, list, P)):
            result = self._numeric_operation(other, operator.mul, "*")
            return 0 if result.case == PCase.ZERO else result
        if isinstance(other, tuple):
            return make_T(other, index=self.index) * self
        if isinstance(other, (F, V)):
            return other * self
        # Let T own its bound-transform rule without a cyclic import.
        return NotImplemented
        # TODO - handle multiplication with other types
        # call multiplication function
        # if isinstance(other, F):
        #     # if other is a function, use it
        #     # let F handle the multiplication
        #     if other.add:
        #         # if the function is an addition, return a function
        #         if self.case in [PCase.NEGNUM, PCase.NEGSET]:
        #             if other.two_type == Elem.P:
        #                 # if the other is a parameter, make it a subtraction
        # return F(one=self * other.one, sub=True, two=self * other.two)
        #             # make it a subtraction
        # return F(one=self * other.one, sub=True, two=self * other.two)

        # return F(one=self * other.one, add=True, two=self * other.two)

        # return F(one=self, mul=True, two=other, one_type=Elem.P)

    def __rmul__(
        self,
        other: Self | ArithmeticOperand | None,
    ) -> P:
        # multiplication is commutative
        return self * other

    def __truediv__(self, other: Self | ArithmeticOperand | None) -> P:
        """Divide values, checking denominators even for zero numerators."""
        return self._numeric_operation(other, operator.truediv, "/")

    def __rtruediv__(self, other):
        """
        Evaluate reflected numeric division in its original operand order.
        """
        other = normalize_operand(other)
        if isinstance(other, (int, float, list, P)):
            return self._numeric_operation(
                other,
                operator.truediv,
                "/",
                reverse=True,
            )
        return self._divide_numeric(1) * other

    def __floordiv__(self, other: Self | ArithmeticOperand | None) -> P:
        """Apply Python floor division, including flooring by one."""
        return self._numeric_operation(other, operator.floordiv, "//")

    def __rfloordiv__(self, other):
        """Apply floor division with the external numerator first."""
        return self._numeric_operation(
            other,
            operator.floordiv,
            "//",
            reverse=True,
        )

    def __rmod__(self, other):
        """Compute remainders with the external dividend first."""
        return self._numeric_operation(other, operator.mod, "%", reverse=True)

    def __rpow__(self, other):
        """Raise external bases to this parameter's numeric exponents."""
        return self._numeric_operation(other, operator.pow, "^", reverse=True)

    def __mod__(self, other: Self | ArithmeticOperand | None) -> P:
        """Compute remainders without shortcuts or recursive fallback."""
        return self._numeric_operation(other, operator.mod, "%")

    def __pow__(self, other: Self | ArithmeticOperand | None) -> P | int:
        """Evaluate powers; exponent zero returns the integer identity."""
        other = normalize_operand(other)
        if other is None:
            return self
        if isinstance(other, (int, float)):
            if other == 0:
                return 1
            if other == 1:
                return self
        return self._numeric_operation(other, operator.pow, "^")

    # endregion

    # region Comparisons

    def _compare_non_numeric(
        self,
        other: object,
        compare: Callable[[float, float], bool],
        symbol: str,
    ) -> bool:
        """Compare known shapes, or return NotImplemented for Python dispatch.

        Preserve scalar/set errors, mismatch warnings and eager pairwise-all
        evaluation (including !=). Scalar comparisons stay inline to avoid
        callbacks on construction hot paths.
        """
        scalar = self.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO)
        if isinstance(other, P):
            values = other._
            kind = "parameter set"
        elif isinstance(other, list):
            values = other
            kind = "list"
        else:
            return NotImplemented

        if scalar:
            message = (
                f"{self} {symbol} {other}: "
                f"cannot compare a number with a {kind}."
            )
            raise NotImplementedError(message)
        if len(self) != len(other):
            warn(
                f"Index mismatch {self} {symbol} {other}: "
                f"len(self) ({len(self)}) != len(other) ({len(other)})",
            )
        return all(list(map(compare, self._, values)))

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """Compare known values; defer unsupported types to reflection."""

        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                if self.case == PCase.ZERO:
                    # if self is zero, return True
                    return True

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] == other
            # Other numeric comparisons require a scalar parameter.
            message = (
                f"{self} == {other}: "
                "cannot compare a parameter set with a number"
            )
            raise NotImplementedError(message)

        if isinstance(other, P) and self.case in (
            PCase.NUM,
            PCase.NEGNUM,
            PCase.ZERO,
        ):
            if other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
                return self._[-1] == other._[-1]

        return self._compare_non_numeric(other, operator.eq, "==")

    def __ne__(
        self,
        other: object,
    ) -> bool:
        """Compare known values; defer unsupported types to reflection."""
        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] != other
            # Other numeric comparisons require a scalar parameter.
            message = (
                f"{self} != {other}: "
                "cannot compare a parameter set with a number"
            )
            raise NotImplementedError(message)

        if isinstance(other, P) and self.case in (
            PCase.NUM,
            PCase.NEGNUM,
            PCase.ZERO,
        ):
            if other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
                return self._[-1] != other._[-1]

        return self._compare_non_numeric(other, operator.ne, "!=")

    def __lt__(
        self,
        other: object,
    ) -> bool:
        """Compare known values; defer unsupported types to reflection."""
        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                if self.case in [PCase.NEGNUM, PCase.NEGSET]:
                    # if self negative number or negated set, return True
                    return True

                if self.case in [PCase.ZERO, PCase.NUM, PCase.SET]:
                    # A positive number or unnegated set is not less than zero.
                    return False

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] < other
            # Other numeric comparisons require a scalar parameter.
            message = (
                f"{self} < {other}: "
                "cannot compare a parameter set with a number"
            )
            raise NotImplementedError(message)

        if isinstance(other, P) and self.case in (
            PCase.NUM,
            PCase.NEGNUM,
            PCase.ZERO,
        ):
            if other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
                return self._[-1] < other._[-1]

        return self._compare_non_numeric(other, operator.lt, "<")

    def __le__(
        self,
        other: object,
    ) -> bool:
        """Compare known values; defer unsupported types to reflection."""

        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                if self.case in [PCase.ZERO, PCase.NEGNUM, PCase.NEGSET]:
                    # if self is zero or negative number, return True
                    return True

                if self.case in [PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return False
                    return False

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] <= other
            # Other numeric comparisons require a scalar parameter.
            message = (
                f"{self} <= {other}: "
                "cannot compare a parameter set with a number"
            )
            raise NotImplementedError(message)

        if isinstance(other, P) and self.case in (
            PCase.NUM,
            PCase.NEGNUM,
            PCase.ZERO,
        ):
            if other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
                return self._[-1] <= other._[-1]

        return self._compare_non_numeric(other, operator.le, "<=")

    def __gt__(
        self,
        other: object,
    ) -> bool:
        """Compare known values; defer unsupported types to reflection."""
        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                if self.case in [PCase.ZERO, PCase.NEGNUM, PCase.NEGSET]:
                    # Zero and negative cases are not greater than zero.
                    return False

                if self.case in [PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return True
                    return True

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] > other
            # Other numeric comparisons require a scalar parameter.
            message = (
                f"{self} > {other}: "
                "cannot compare a parameter set with a number"
            )
            raise NotImplementedError(message)

        if isinstance(other, P) and self.case in (
            PCase.NUM,
            PCase.NEGNUM,
            PCase.ZERO,
        ):
            if other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
                return self._[-1] > other._[-1]

        return self._compare_non_numeric(other, operator.gt, ">")

    def __ge__(
        self,
        other: object,
    ) -> bool:
        """Compare known values; defer unsupported types to reflection."""
        other = normalize_operand(other)
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                if self.case in [PCase.NEGNUM, PCase.NEGSET]:
                    # if self negative number or negated set, return False
                    return False

                if self.case in [PCase.ZERO, PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return True
                    return True

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] >= other
            # Other numeric comparisons require a scalar parameter.
            message = (
                f"{self} >= {other}: "
                "cannot compare a parameter set with a number"
            )
            raise NotImplementedError(message)

        if isinstance(other, P) and self.case in (
            PCase.NUM,
            PCase.NEGNUM,
            PCase.ZERO,
        ):
            if other.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO):
                return self._[-1] >= other._[-1]

        return self._compare_non_numeric(other, operator.ge, ">=")

    # endregion

    # region Matrix representation

    @property
    def A(self) -> list[list[float]]:
        """Generate a diagonal matrix representation of the variable set"""
        return [[self._[i]] for i in range(len(self))]

    # endregion

    # region Display and representation

    @property
    def ltx(self) -> str:
        """Render the shared escaped name in parameter-specific roman type."""
        return r"{\mathrm{" + self._latex_name() + r"}}"

    @property
    def index_ltx(self) -> str:
        """Render grouped coordinates before inspecting singleton axes."""
        if isinstance(self.index, set):
            groups = (",".join(i.ltx for i in idx) for idx in self.index)
            return "(" + ")|(".join(groups) + ")"
        if len(self.index) == 1:
            return self.index[0].ltx
        return ",".join(
            i.ltx if not isinstance(i, list) else i[0].ltx for i in self.index
        )

    def latex(self) -> str:
        """
        LaTeX representation

        :returns: LaTeX representation of the parameter set
        :rtype: str
        """

        if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
            return str(self)
        return self.ltx + r"_{" + self.index_ltx + r"}"

    def show(self, descriptive: bool = False):
        """Display the variables

        Args:
            descriptive (bool, optional): If True, shows all parameters.
            Defaults to False.
        """
        if descriptive:
            # just print out the parameters
            for p in self._:
                print(p)

        super().show()

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
        Plot the parameter set

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
            data=self._,
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
        Plot the parameter set

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
            data=self._,
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
    # "⚠ sympy is an optional dependency, pip install gana[all] to get optional
    # dependencies ⚠"
    #     )

    # def pyomo(self):
    #     """Pyomo representation"""
    #     # idx = [i.pyomo() for i in self.index]
    #     # return PyoParam(*idx, initialize=self._, doc=str(self))
    #     if has_pyomo:
    #         return PyoParam(
    #             initialize=self._,
    #             doc=str(self),
    #         )
    #     logger.warning(
    # "pyomo is an optional dependency, pip install gana[all] to get optional
    # dependencies"
    #     )

    # endregion
