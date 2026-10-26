"""
Lazy symbolic facades and registries over native coordinate/member owners.
"""

from __future__ import annotations

import operator
from bisect import bisect_right
from collections.abc import (
    ItemsView,
    MutableMapping,
    MutableSequence,
    Sequence,
)
from importlib import import_module
from typing import TYPE_CHECKING, Any
from weakref import WeakValueDictionary

from ..indexing import selection
from ..indexing.coordinates import (
    Positions,
    decode_bounds,
    encode_bounds_batch,
)
from ..utils._display import MappingPreview, SequencePreview

if TYPE_CHECKING:
    from ..sets.theta import T
    from ..sets.variable import V

STRUCTURAL = (
    "Native symbolic members cannot be replaced or reordered; "
    "use mutable program reassignment to grow the owner"
)


def guard_attribute(element: Any, name: str, value: Any) -> None:
    """Protect registered native facades while allowing declaration edits."""
    if name in {"_", "map"} and "_symbol_storage" in element.__dict__:
        raise TypeError(STRUCTURAL)
    object.__setattr__(element, name, value)


class SymbolStorage:
    """
    Keep native membership authoritative and cache only live scalar wrappers.
    """

    def __init__(self, root, positions, owner=None):
        """
        Selections share their root's wrapper lookup and mutable member state.
        """
        self.root, self.positions = root, positions
        self.owner = self if owner is None else owner
        if owner is None:
            self.cache: WeakValueDictionary[int, V | T] = WeakValueDictionary()
            self.states = {}
            self.template_starts = [0]
            self.templates = [root._member_template()]

    def install(self, element):
        """
        Attach synchronized read facades without enumerating scalar members.
        """
        object.__setattr__(element, "_symbol_storage", self)
        object.__setattr__(element, "_", SymbolValues(self))
        object.__setattr__(element, "map", SymbolMap(self))

    def member(self, position):
        """
        Reuse a live wrapper by stable owner ID, creating it only on demand.
        """
        owner = self.owner
        member_id = self.positions.handle.id(position)
        member = owner.cache.get(member_id)
        if member is None:
            # Defer concrete V/T subclasses until module imports finish.
            factory = import_module(
                ".members",
                __package__,
            ).make_member
            member = factory(owner, member_id)
            owner.cache[member_id] = member
        return member

    def select(self, element, axes=None, *, allow_missing=False):
        """
        Pin membership while retaining shared symbolic records and scalar
        identity. Return False for permitted gaps so the caller can attach
        lazy placeholder containers without replaying Python lookups.
        """
        if axes is None:
            positions = self.positions.freeze()
        else:
            selected = self.positions.product(
                axes,
                allow_missing=allow_missing,
            )
            if selected is None:
                return False
            positions = selected[0]
        SymbolStorage(self.root, positions, self.owner).install(element)
        return True

    def append(self, keys, start, bounds=None):
        """
        Commit native coordinates and column IDs without materializing
        children.
        """
        pairs = (
            [None] * len(keys)
            if bounds is None
            else encode_bounds_batch(bounds)
        )
        starts = [*self.template_starts, len(self.positions)]
        templates = [*self.templates, self.root._member_template()]
        self.positions.owner.append(
            keys,
            list(range(start, start + len(keys))),
            pairs,
        )
        self.template_starts, self.templates = starts, templates

    def template(self, member_id):
        """
        Resolve metadata captured when this member's registration span was
        accepted.
        """
        return self.templates[
            bisect_right(self.template_starts, member_id) - 1
        ]

    def bounds(self):
        """
        Read validated theta intervals without instantiating scalar wrappers.
        """
        return [
            decode_bounds(pair) for pair in self.positions.handle.all_bounds()
        ]

    def __getstate__(self):
        """
        Retain live identities in the serialized graph without serializing
        weakrefs.
        """
        self._finish_constraint_rows()
        state = {
            key: value
            for key, value in self.__dict__.items()
            if key != "cache"
        }
        state["live_members"] = dict(self.cache) if self.owner is self else {}
        return state

    def _finish_constraint_rows(self):
        """Complete exposed memberships before copying their mutable states.

        A later constraint serialization must not append links after this
        owner's dictionaries have already been copied into the new graph.
        """
        for constraint in tuple(self.__dict__.get("constraint_links", ())):
            if constraint.__dict__.get(
                "_native_rows",
            ) or constraint.__dict__.get(
                "_native_linked_members",
            ):
                constraint._materialize()

    def __setstate__(self, state):
        """Restore lookup machinery without retaining dead wrapper objects."""
        members = state.pop("live_members")
        self.__dict__.update(state)
        self.cache = WeakValueDictionary(members)


class SymbolValues(SequencePreview, MutableSequence):
    """
    Lazy list-compatible reads; structural writes cannot corrupt native IDs.
    """

    def __init__(self, storage):
        """
        Keep membership and its owner alive for the facade's entire lifetime.
        """
        self.storage = storage

    def __len__(self):
        """Count native members without constructing wrappers."""
        return len(self.storage.positions)

    def __getitem__(self, position):
        """
        Slices explicitly materialize detached lists; scalar access is lazy.
        """
        if isinstance(position, slice):
            return [self.storage.member(n) for n in range(len(self))[position]]
        return self.storage.member(range(len(self))[operator.index(position)])

    def __iter__(self):
        """Traverse members in native insertion order."""
        return (self.storage.member(n) for n in range(len(self)))

    def copy(self):
        """Return an ordinary detached list of shared symbolic members."""
        return list(self)

    def __eq__(self, other):
        """
        Preserve list comparison, including its shared-object identity
        shortcut.
        """
        return list(self) == (
            list(other) if isinstance(other, SymbolValues) else other
        )

    def __setitem__(self, _position, _value):
        """Reject raw member replacement before any owner state changes."""
        raise TypeError(STRUCTURAL)

    def __delitem__(self, _position):
        """Reject raw deletion before any owner state changes."""
        raise TypeError(STRUCTURAL)

    def insert(self, _position, _value):
        """Raw growth must use the program's validated mutation operation."""
        raise TypeError(STRUCTURAL)

    def reverse(self):
        """Reordering would change coordinate-aligned membership."""
        raise TypeError(STRUCTURAL)


class SymbolItems(ItemsView):
    """A retained items view sees future root growth when iteration begins."""

    _mapping: SymbolMap

    def __iter__(self):
        """
        Traverse keys and members together without repeated coordinate lookups.
        """
        return zip(self._mapping, self._mapping.values())


class SymbolMap(MappingPreview, MutableMapping):
    """Ordered coordinate lookup over the same owner as the sequence facade."""

    def __init__(self, storage):
        """Retain the common symbolic owner and membership selector."""
        self.storage = storage

    def __len__(self):
        """Count membership without creating keys or scalar wrappers."""
        return len(self.storage.positions)

    def __iter__(self):
        """Decode coordinates in stable owner order."""
        return iter(self.storage.positions)

    def __getitem__(self, key):
        """Resolve a coordinate and reuse its live scalar wrapper."""
        return self.storage.member(self.storage.positions[key])

    def __contains__(self, key):
        """Membership must never instantiate an otherwise unused scalar."""
        return key in self.storage.positions

    def values(self):
        """
        Traverse directly instead of repeatedly hashing decoded coordinates.
        """
        return SymbolValues(self.storage)

    def items(self):
        """
        Pair ordered coordinates and members without redundant native lookup.
        """
        return SymbolItems(self)

    def copy(self):
        """Materialize an explicitly requested detached dictionary."""
        return dict(self.items())

    def __setitem__(self, _key, _value):
        """Reject raw member replacement before any owner state changes."""
        raise TypeError(STRUCTURAL)

    def __delitem__(self, _key):
        """Reject raw deletion before any owner state changes."""
        raise TypeError(STRUCTURAL)


class SymbolRegistry(Sequence):
    """
    Program-global column order stored as owner spans, without scalar lists.
    """

    def __init__(self):
        """Start with no registered spans or materialized members."""
        self.spans, self.ends = [], []

    def add(self, root, start=0):
        """
        Append the accepted owner suffix in O(1), preserving interleaved
        growth.
        """
        length = len(root) - start
        if length:
            self.spans.append((root, start))
            self.ends.append(len(self) + length)

    def __len__(self):
        """Return the number of registered model columns."""
        return self.ends[-1] if self.ends else 0

    def __getitem__(self, position):
        """
        Locate a span by binary search; slices return detached member lists.
        """
        if isinstance(position, slice):
            return [self[n] for n in range(len(self))[position]]
        position = range(len(self))[operator.index(position)]
        span = bisect_right(self.ends, position)
        root, start = self.spans[span]
        offset = self.ends[span - 1] if span else 0
        return root[start + position - offset]

    def __eq__(self, other):
        """
        Retain historical list comparisons without using symbolic equality
        internally.
        """
        return list(self) == (
            list(other) if isinstance(other, SymbolRegistry) else other
        )


def register(root, start, bounds=None):
    """Create native V/T storage after declaration validation succeeds."""
    keys = root.map
    pairs = (
        [None] * len(keys) if bounds is None else encode_bounds_batch(bounds)
    )
    positions = Positions.create(
        keys,
        list(range(start, start + len(keys))),
        pairs,
    )
    SymbolStorage(root, positions).install(root)


def select(source, target, axes=None, *, kind="v"):
    """Normalize requested axes only when native membership is available."""
    if axes is not None and selection.reselect(source, target, axes, kind):
        return True
    storage = getattr(source, "_symbol_storage", None)
    if storage is None:
        return False
    if axes is None:
        storage.select(target)
        return True
    axes = selection.axes_snapshot(axes)
    if selection.has_placeholders(axes):
        _select_placeholders(storage, target, axes, kind)
        return True
    if not storage.select(target, axes, allow_missing=kind == "v"):
        _select_placeholders(storage, target, axes, kind)
    return True


def _select_placeholders(storage, target, axes, kind):
    """Preserve gap policies and freeze membership without creating members."""
    if kind == "t":
        storage.positions.product(selection.valid_axes(axes, kind))
    frozen = SymbolStorage(
        storage.root,
        storage.positions.freeze(),
        storage.owner,
    )
    selection.install(target, SymbolMap(frozen), axes, kind)
