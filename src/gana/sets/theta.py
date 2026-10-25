# """Parametric variable"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from itertools import product

# from functools import reduce
from math import isfinite, isnan
from numbers import Real
from typing import Self, cast

from gana.types import Number

from ..indexing.staging import fill_map
from ..storage import symbols as symbol_storage
from ._element import _E
from .birth import make_P
from .constraint import C
from .function import F
from .index import I
from .operands import normalize_operand, reject_disequality
from .parameter import P
from .variable import V

# Preserve original union members; keep Self at use sites.
type ThetaOperand = P | V | F


class T(_E["T | tuple[float, ...] | None"]):
    """
    Ordered set of parametric variables (theta).

    :param index: Index for the theta set.
    :type index: I
    :param _: Values for the theta set.
    :type _: list[tuple[float]] | tuple[float]
    :param mutable: If True, the theta set can be modified. Defaults to False.
    :type mutable: bool, optional
    :param tag: Tag for the theta set. Defaults to None.
    :type tag: str, optional

    :ivar index: Index of the parametric variable set
    :vartype index: I
    :ivar _: List of parametric variables
    :vartype _: list[int | float]
    :ivar mutable: If the parametric variable set is mutable
    :vartype mutable: bool
    :ivar tag: Tag/details
    :vartype tag: str
    :ivar name: Name, set by the program
    :vartype name: str
    :ivar n: Number id, set by the program
    :vartype n: int
    :ivar map: Index to parameter mapping
    :vartype map: dict[X | Idx, Var]
    """

    # Only a growing root needs an instance counter; scalar members share this
    # default.
    n_splices = 1
    _compact_staging = True
    # Preserve generated algebraic labels independently of registry keys.
    _derived_name: str | None = None
    # Internal affine snapshots retain the original public operand for replay.
    _native_theta_source: T

    # Registered owners protect their native facades; staging stays editable.
    __setattr__ = symbol_storage.guard_attribute

    # region Construction and validation

    def __init__(
        self,
        *index: I,
        _: Sequence[tuple[float, ...]] | tuple[float, ...] | None = None,
        tag: str | None = None,
        mutable: bool = False,
        ltx: str | None = None,
        name: str = "",
    ):
        """Normalize intervals before registration creates symbolic members."""
        _E.__init__(self, *index, tag=tag, ltx=ltx, mutable=mutable, name=name)

        # name will be set by the program later
        # if dummy index, the name is set to 'φ' (phi)
        self.name = self.name or "θ"

        self.lb: Number | None = None
        self.ub: Number | None = None

        # flag to check if the set has been birthed
        self.birthed = False
        if _ is not None:
            self._initialize_bounds(_)

    @staticmethod
    def _bound_pair(bounds) -> tuple[float, float]:
        """Validate one closed interval, allowing infinite endpoints."""
        # Ordinary tuples cannot be T instances. Avoid an abstract-class check
        # for every row while retaining subclass and existing-member behavior.
        if type(bounds) is not tuple and isinstance(bounds, T):
            bounds = (bounds.lb, bounds.ub)
        endpoints = 2
        if not isinstance(bounds, tuple) or len(bounds) != endpoints:
            message = "Theta bounds require a (lower, upper) pair"
            raise ValueError(message)
        lower, upper = bounds
        numeric = (int, float, Real)
        if not isinstance(lower, numeric) or not isinstance(upper, numeric):
            message = "Theta bounds must be numeric"
            raise TypeError(message)
        if (
            isnan(lower)
            or isnan(upper)
            or cast(Real, lower) > cast(Real, upper)
        ):
            message = "Theta bounds must be ordered and cannot contain NaN"
            raise ValueError(message)
        # Preserve integer precision and avoid allocating two floats per
        # member.
        return bounds

    def _initialize_bounds(self, bounds):
        """Normalize scalar or per-coordinate bounds before registration."""
        if isinstance(bounds, tuple):
            self._implicit_index(1)
            self._ = [bounds] * len(self.map)
        else:
            self._ = list(bounds)
            self._implicit_index(len(self._))
        self._validated_bounds()
        self.create_map()

    def _validated_bounds(self) -> list[tuple[float, float]]:
        """Validate afresh before registry changes, batching built-ins in Rust.

        Subclasses and existing members use the same Python validator, in
        row order. The returned list is detached from editable staging.
        """
        native = getattr(self, "_symbol_storage", None)
        if native is not None:
            return native.bounds()
        if len(self._) != len(self.map):
            message = "Theta bounds length must match its coordinates"
            raise ValueError(message)
        if type(self) is T:
            return import_module("gana._native").validate_bounds(
                self._,
                self._bound_pair,
            )
        return [self._bound_pair(bounds) for bounds in self._]

    def _member_template(self):
        """
        Capture display metadata before lazy access can observe later root
        edits.
        """
        # Generated labels already contain the transformation and member name;
        # inheriting the root's LaTeX would hide a member's leading sign.
        return {
            "name": self.name,
            "args": {
                "tag": self.tag,
                "ltx": None if self._derived_name else self.ltx,
                "mutable": self.mutable,
            },
        }

    def _new_member(
        self,
        key,
        position,
        number,
        bounds,
        *,
        template=None,
    ) -> T:
        """
        Create one accepted coordinate with its final owner and global ID.
        """
        if template is None:
            theta = T(
                tag=self.tag,
                ltx=None if self._derived_name else self.ltx,
                mutable=self.mutable,
            )
            name = self.name
        else:
            theta = T(**template["args"])
            name = template["name"]
        theta.parent = self
        theta.n, theta.pos = number, position
        theta.name = f"{name}[{position}]"
        theta.index = key
        theta.lb, theta.ub = bounds
        theta._ = [theta]
        theta.map[key] = theta
        theta.birthed = True
        return theta

    def birth_thetas(self, mutating: bool = False, n_start=0):
        """
        Populate once after validation; retain ``mutating`` for compatibility.
        """
        del mutating
        if self.birthed:
            return
        bounds = self._validated_bounds()
        self._birth_validated(bounds, n_start)

    def _birth_validated(self, bounds, n_start=0):
        """Populate from a freshly validated batch without a second traversal.

        Registration validates before naming or binding the owner. Its accepted
        batch is consumed immediately here; no cached validation survives edits
        to an unregistered declaration. Direct birth validates in its public
        entry point before reaching this helper.
        """
        if self.birthed:
            return
        symbol_storage.register(self, n_start, bounds)
        self.birthed = True

    def create_map(self):
        """Refresh values while preserving the tuple coordinate convention."""
        if len(self.map) != len(self._):
            message = "Theta bounds length must match its coordinates"
            raise ValueError(message)
        fill_map(self.map, self._)

    # endregion

    # region Indexing and selection

    @property
    def _owner_root(self) -> T:
        """
        Retain the concrete theta type through shared selection ownership.
        """
        return cast("T", super()._owner_root)

    def _row_reference(self, key: tuple) -> T:
        """Retain an aligned anonymous coordinate without building a selection.

        The expression compiler has already checked membership. Public
        selections still use ``__call__``; only internal scalar operands take
        this path, before their owner has registered scalar members.
        """
        index = self._normalize_index(key)
        return self if index == self.index else _ThetaRow(self, key, index)

    def __call__(self, *key: I) -> T:
        """Share selected members; new selections are concrete T instances."""
        key = self._normalize_index(key)
        if not key or (key == self.index):
            # if the index is an exact match
            # or no key is passed
            return self

        # if a subset is passed,
        # first create a product to match
        # the indices
        indices = product(*key)

        # create a new variable set to return
        t = self._new_selection(
            T(tag=self.tag, ltx=self.ltx, mutable=self.mutable),
            key,
        )
        if not symbol_storage.select(self, t, key, kind="t"):
            for index in indices:
                # Preserve legacy placeholders at shifted boundaries.
                if any(i is None for i in index):
                    theta = None
                else:
                    theta = self.map[index]
                    t.map[index] = theta
                t._.append(theta)
        t.birthed = self.birthed
        return t

    # endregion

    # region Unary operations

    def __neg__(self):
        """Reflect each interval about zero, preserving ordered endpoints."""
        result = self._scale_bounds(-1)
        result.name = result._derived_name = f"-{self._factor_name()}"
        return result

    # endregion

    # region Arithmetic helpers

    def _coerce_operand(self, other):
        """
        Wrap numeric and interval operands without transforming theta bounds.
        """
        if isinstance(other, (int, float)):
            return make_P(other, self.index)
        if isinstance(other, tuple):
            return T(*self.index, _=other)
        if isinstance(other, list):
            return T(_=other) if isinstance(other[0], tuple) else make_P(other)
        return other

    def _scale_coefficients(self, other):
        """Broadcast finite constants or require one value per selected row."""
        values, scalar, _ = P._numeric_payload(other)
        if not all(isfinite(value) for value in values):
            message = "Theta scaling requires finite coefficients"
            raise ValueError(message)
        if scalar:
            return [values[-1]] * len(self)
        if len(values) != len(self):
            message = "Theta scaling requires one coefficient per interval"
            raise ValueError(message)
        return values

    @staticmethod
    def _scaled_pair(bounds, coefficient, divide):
        """Order negative products; zero times any interval is exactly zero."""
        if divide:
            values = tuple(value / coefficient for value in bounds)
        elif coefficient == 0:
            return (0, 0)
        else:
            values = tuple(value * coefficient for value in bounds)
        return min(values), max(values)

    def _factor_name(self):
        """Group generated or signed labels before a further transformation."""
        name = str(self)
        return f"({name})" if any(c in name for c in "+-*/") else name

    def _scale_bounds(self, other, divide=False):
        """Create an independent interval owner, retaining coordinate order.

        Direct T scaling snapshots transformed bounds, including for factors
        zero and one. Reusing the result reuses that owner. Scaling an F
        changes coefficients and retains the referenced owners.
        """
        coefficients = self._scale_coefficients(other)
        values = [
            self._scaled_pair(pair, scale, divide)
            for pair, scale in zip(self._validated_bounds(), coefficients)
        ]
        label = normalize_operand(other)
        name = (
            f"{self._factor_name()}/({label})"
            if divide
            else f"{label}*{self._factor_name()}"
        )
        result = T(*self.index, tag=self.tag, mutable=self.mutable, name=name)
        result._ = values
        result.map = dict(zip(self.map, values))
        result._validated_bounds()
        result._derived_name = name
        return result

    # endregion

    # region Binary arithmetic

    def __add__(self, other):
        """
        Form an affine expression retaining all theta coordinate references.
        """
        other = normalize_operand(other)
        if other is None:
            return self
        return F(one=self, two=self._coerce_operand(other), add=True)

    def __radd__(self, other: Self | ThetaOperand):
        """Use theta addition without re-entering reflected dispatch."""
        return self + other

    def __sub__(self, other):
        """
        Form an affine expression retaining all theta coordinate references.
        """
        other = normalize_operand(other)
        if other is None:
            return self
        return F(one=self, two=self._coerce_operand(other), sub=True)

    def __rsub__(self, other: Self | ThetaOperand):
        """Subtract the original theta without allocating a negated owner."""
        other = self._coerce_operand(normalize_operand(other))
        return F(one=other, two=self, sub=True)

    def __mul__(self, other: Self | F | Number):
        """Return new bounds, with the coefficient first in the label."""
        return self._scale_bounds(other)

    def __rmul__(self, other: Self | F | int):
        """Scale intervals in either operand order."""
        return self * other

    def __truediv__(self, other: Self | F | int):
        """Return independent bounds divided by nonzero real coefficients."""
        return self._scale_bounds(other, divide=True)

    # endregion

    # region Comparisons

    def __eq__(self, other):
        """Build an equality, including constraints containing only thetas."""
        return C(self - other)

    def __ne__(self, other):
        """Reject a symbolic disequality instead of returning a boolean."""
        reject_disequality()

    def __le__(self, other):
        """Build an affine upper bound without changing interval bounds."""
        return C(self - other, leq=True)

    def __lt__(self, other):
        """Retain Gana's convention that strict bounds mean weak bounds."""
        return self <= other

    def __ge__(self, other):
        """Build an affine lower bound, retaining theta identity."""
        return C(self.__rsub__(other), leq=True)

    def __gt__(self, other):
        """Retain Gana's convention that strict bounds mean weak bounds."""
        return self >= other

    # endregion

    # region Matrix representation

    @property
    def CrA(self):
        """Build bound rows with integer zeros and floating diagonals."""
        CrA_UB: list[list[float]] = [[0] * len(self) for _ in range(len(self))]
        CrA_LB: list[list[float]] = [[0] * len(self) for _ in range(len(self))]

        for n in range(len(self)):
            CrA_UB[n][n] = 1.0
            CrA_LB[n][n] = -1.0

        CrA_ = []

        for n in range(len(self)):
            CrA_.append(CrA_UB[n])
            CrA_.append(CrA_LB[n])

        return CrA_

    @property
    def CrB(self):
        """Return upper and negated lower bounds in member order."""
        return [
            value
            for lower, upper in self._validated_bounds()
            for value in (upper, -lower)
        ]

    # endregion

    # region Display and representation

    @property
    def ltx(self) -> str | None:
        """LaTeX representation of the parametric variable set"""
        if self._ltx:
            return r"{" + self._ltx + r"}"
        # if user has not set the LaTeX representation
        # the name becomes the latex representation
        if self.name:
            name = self.name.replace("_", r"\_")
            if name.startswith("-"):
                return "-{" + name[1:] + "}"
            return "{" + name + "}"
        return self._ltx

    def latex(self) -> str:
        """Render initialized labels; erased labels retain their TypeError."""

        index = (
            r"_{"
            + rf"{self.index}".replace("(", "")
            .replace(")", "")
            .replace("[", "{")
            .replace("]", "}")
            + r"}"
        )

        if len(self.index) == 1:
            # if there is a single index element
            # then a comma will show up in the end, replace that
            return cast(str, self.ltx) + index.replace(",", "")

        return cast(str, self.ltx) + index

    # endregion


class _ThetaRow(T):
    """Compact, strongly owned theta coordinate used by an expression row.

    Keep the selection's display metadata, but defer its legacy list and map
    until an operation actually requests them. Ordinary expression assembly,
    printing and registration need only the owner, coordinate and label.
    Bounds and column IDs remain on the owner, including after registration.

    Inheriting T preserves symbolic dispatch and its arithmetic contract. The
    base has an instance dictionary; slots keep it unpopulated on the common
    construction path. Explicit row arithmetic can populate that dictionary
    with the same small containers that a public selection would expose.
    """

    __slots__ = (
        "_coordinate",
        "_ltx",
        "_selection_owner",
        "index",
        "mutable",
        "name",
        "tag",
    )

    # Anonymous selections have no independent registration or scalar bounds.
    n = parent = pos = lb = ub = None
    birthed = False

    def __init__(self, source: T, key: tuple, index: tuple):
        """Capture selection metadata without initializing an element tree."""
        self._selection_owner = source._owner_root
        self._coordinate, self.index = key, index
        self.name = source.name
        self.tag, self.mutable = source.tag, source.mutable
        self._ltx = source.ltx

    def __len__(self) -> int:
        """An aligned row always addresses exactly one existing coordinate."""
        return 1

    def __getattr__(self, name: str):
        """Materialize compatibility containers only when explicitly read.

        Resolve against the owner so a row used after registration sees the
        registered member. Missing metadata must remain missing: in particular
        this reference never gains the owner's registration token or name.
        """
        if name not in {"_", "map", "elements"}:
            raise AttributeError(name)
        value = self._owner_root.map[self._coordinate]
        self._ = [value]
        self.map = {self._coordinate: value}
        self.elements = [self]
        return self.__dict__[name]
