"""Shared storage, metadata, and selection helpers for indexed elements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from itertools import product
from typing import Generic, Self, TypedDict, TypeVar, cast, overload

from IPython.display import Math, display

from ..indexing.staging import CartesianMap
from .index import I
from .operands import NumericDispatch

_Member = TypeVar("_Member")
_Selection = TypeVar("_Selection", bound="_E")


class _ElementArgs(TypedDict):
    """Constructor metadata with distinct text and mutability fields.

    Keep the ordinary dictionary payload while allowing callers to unpack
    its known keys without treating every value as a string/boolean union.
    """

    tag: str | None
    ltx: str | None
    mutable: bool


class _E(NumericDispatch, ABC, Generic[_Member]):
    """Common contract for indexed parameters, variables, and thetas.

    Subclasses supply selection and LaTeX semantics. Arithmetic, missing-index
    policies, and scalar creation remain with each concrete element type.
    Members may be numerical values or symbolic objects; storage does not
    require members to have the same type as their containing collection.
    """

    # Registration metadata is added only on roots; selections retain their
    # owner.
    _program_token: object
    _registration_name: str
    _selection_owner: _E | None
    _compact_staging = False

    # region Construction and ownership

    def __init__(
        self,
        *index: I,
        tag: str | None = "",
        ltx: str | None = "",
        mutable: bool = False,
        name: str = "",
    ):
        """Initialize metadata and retain index traversal order."""
        self.tag = tag
        self._ltx = ltx
        self.mutable = mutable
        self.name = name
        self.index, self.map = self._prepare_index(index)
        self.n: int | None = None
        self.parent: Self | None = None
        self.pos: int | None = None
        self._: list[_Member] = []
        self.elements = [self]

    def __init_subclass__(cls, **kwargs):
        """Retain hashing for subclasses that overload symbolic equality."""
        super().__init_subclass__(**kwargs)
        for name, method in (
            ("__repr__", _E.__repr__),
            ("__hash__", _E.__hash__),
        ):
            setattr(cls, name, method)

    @property
    def args(self) -> _ElementArgs:
        """Return shared constructor options with existing LaTeX values."""
        return {"tag": self.tag, "ltx": self.ltx, "mutable": self.mutable}

    @property
    def _owner_root(self) -> _E:
        """
        Resolve ownership without retaining a program or copying its registry.
        """
        if self.parent is not None:
            return self.parent
        selected = getattr(self, "_selection_owner", None)
        return self if selected is None else selected

    # endregion

    # region Indexing and selection

    @staticmethod
    def _normalize_index(index: tuple) -> tuple:
        """Treat a variable used as an index as one item, not its members."""
        # V imports _E; resolve its type after module initialization.
        from .variable import V

        return tuple([item] if isinstance(item, V) else item for item in index)

    @staticmethod
    def _unpack_index(index: Iterable) -> tuple:
        """Unwrap singleton variable indices for exact-key matching."""
        return tuple(
            item[0] if isinstance(item, list) else item for item in index
        )

    def _prepare_index(
        self,
        index: tuple,
    ) -> tuple[tuple | set[tuple], dict | CartesianMap]:
        """Build dense or union-of-products keys without changing their order.

        Tuple groups are expanded before converting the groups to a set, as
        in the original implementation. This preserves map insertion order.
        An absent index keeps an empty map, without an empty-tuple key.
        """
        if any(isinstance(item, tuple) for item in index):
            groups = [self._normalize_index(group) for group in index]
            mapping = dict.fromkeys(
                key for group in groups for key in product(*group)
            )
            return set(groups), mapping
        normalized = self._normalize_index(index)
        if self._uses_compact_staging(normalized):
            return normalized, CartesianMap(normalized)
        mapping = dict.fromkeys(product(*normalized)) if normalized else {}
        return normalized, mapping

    def _uses_compact_staging(self, axes: tuple) -> bool:
        """Optimize native P/V/T with ordinary I axes; retain generic behavior.

        Custom iterables and index subclasses retain their original traversal
        and hashing behavior. Union domains keep explicit insertion order.
        """
        return bool(
            self._compact_staging
            and axes
            and all(type(axis) is I for axis in axes),
        )

    def _implicit_index(self, size: int) -> None:
        """
        Give indexless numeric payloads real coordinates, including scalars.
        """
        if not self.index and size:
            self._implicit_coordinates = True
            self.index, self.map = self._prepare_index(
                (I(size=size, dummy=True),),
            )

    def _merged_index(self, other: _E) -> set[tuple]:
        """Flatten existing unions before adding another product domain.

        Mapping insertion order remains authoritative for member positions;
        this metadata records domains, not a new traversal of stored values.
        """
        current = (
            self.index
            if isinstance(self.index, set)
            else {self._unpack_index(self.index)}
        )
        incoming = (
            other.index
            if isinstance(other.index, set)
            else {self._unpack_index(other.index)}
        )
        return current | incoming

    def _new_selection(
        self,
        selection: _Selection,
        index: tuple,
    ) -> _Selection:
        """Attach shared identity metadata to a subclass-created selection.

        Each subclass still chooses its constructor and populates its own
        members. Case labels, missing keys, and aliasing retain their existing
        subclass-specific behavior.
        """
        selection.name, selection.n = self.name, self.n
        selection.index = index
        selection._selection_owner = self._owner_root
        return selection

    @abstractmethod
    def __call__(self, *key: I) -> Self:
        """Select indices using the concrete element's lookup policy."""

    @overload
    def __getitem__(self, pos: int) -> _Member:
        """Return one member by its storage position."""
        ...

    @overload
    def __getitem__(self, pos: slice) -> list[_Member]:
        """Return a positional slice of stored members."""
        ...

    def __getitem__(self, pos: int | slice) -> _Member | list[_Member]:
        """Preserve list indexing, slicing, and member identity."""
        return self._[pos]

    def __iter__(self) -> Iterator[_Member]:
        """Iterate over stored numerical or symbolic members in order."""
        return iter(self._)

    def __len__(self) -> int:
        """Count mapped entries; V overrides this to count members."""
        return len(self.map)

    # endregion

    # region Display and representation

    def _latex_name(self) -> str:
        """Cache the escaped name used by parameter and variable rendering."""
        if not self._ltx:
            self._ltx = self.name.replace("_", r"\_")
        return self._ltx

    @property
    def longname(self) -> str:
        """Render ordinary axes or grouped coordinates in their own order."""
        name = self.parent.name if self.parent else self.name
        groups = self.index if isinstance(self.index, set) else (self.index,)
        return (
            name
            + "("
            + ")|(".join(
                ",".join(self._coordinate_name(i) for i in group)
                for group in groups
            )
            + ")"
        )

    @staticmethod
    def _coordinate_name(index):
        """Variable axes retain a singleton member list instead of an I."""
        return (
            index[0].name if isinstance(index, (list, tuple)) else index.name
        )

    @property
    @abstractmethod
    def ltx(self) -> str | None:
        """Return this element type's formatted LaTeX symbol."""

    @abstractmethod
    def latex(self) -> str:
        """Return the complete type-specific LaTeX representation."""

    def show(self, descriptive: bool = False):
        """Display a collection or its nonempty symbolic members.

        Parameters override descriptive output because their members are
        Python numbers. Variable and theta members share this display path.
        """
        if descriptive:
            for member in self._:
                if member:
                    # P overrides this path; V/T supply symbolic members.
                    display(Math(cast("_E", member).latex()))
        else:
            display(Math(self.latex()))

    def __str__(self) -> str:
        """Return the registered or generated name."""
        return self.name

    def __repr__(self) -> str:
        """Use the same name when displaying collections of elements."""
        return self.name

    def __hash__(self) -> int:
        """Preserve name-based hashing and the existing unpickling fallback."""
        try:
            return hash(self.name)
        except AttributeError:
            return id(self)

    # endregion
