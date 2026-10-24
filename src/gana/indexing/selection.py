"""Lazy compatibility containers for skipped, missing or repeated coordinates.

Regular native selections use the native storage facades. These exceptional
selections preserve Python's distinct list/map semantics, including independent
container edits, without allocating a scalar member per requested coordinate.
"""

from collections.abc import MutableMapping, MutableSequence
from itertools import islice, product
from math import prod

from ..utils._display import MappingPreview, SequencePreview


def axes_snapshot(axes):
    """
    Freeze membership once per axis; subsequent index edits cannot change
    it.
    """
    return tuple(tuple(axis) for axis in axes)


def has_placeholders(axes):
    """
    Detect skipped or repeated axis entries without expanding their
    product. A missing entry is identified by identity: symbolic equality
    may construct constraints instead of returning a Boolean.
    """
    return any(
        any(atom is None for atom in axis) or len(set(axis)) != len(axis)
        for axis in axes
    )


def valid_axes(axes, kind):
    """P/T skip None coordinates, whereas V attempts every requested tuple."""
    if kind == "v":
        return axes
    return tuple(
        tuple(atom for atom in axis if atom is not None) for axis in axes
    )


class Selection:
    """
    A fixed product domain over a retained source mapping, including gaps.
    """

    def __init__(self, source, axes, kind):
        """Retain axes and source ownership; scalar reads remain deferred."""
        self.source, self.axes, self.kind = source, axes, kind
        self.unique = tuple(tuple(dict.fromkeys(axis)) for axis in axes)
        self.membership = tuple(frozenset(axis) for axis in self.unique)
        self.size = prod(map(len, axes))
        self.valid = valid_axes(self.unique, kind)
        # Skip only the actual placeholder, without invoking symbolic equality.
        self.skipped = self.size > 0 and any(
            atom is None for axis in axes for atom in axis
        )

    def key(self, position):
        """
        Decode a list position in row-major order using only axis lengths.
        """
        position = range(self.size)[position]
        result = []
        for axis in reversed(self.axes):
            position, offset = divmod(position, len(axis))
            result.append(axis[offset])
        return tuple(reversed(result))

    def value(self, key):
        """
        Read captured values or shared symbols with the historical gap
        policy.
        """
        if self.kind != "v" and any(atom is None for atom in key):
            return None
        if self.kind == "v":
            return self.source.get(key)
        return self.source[key]

    def keys(self):
        """
        Yield unique map keys in insertion order, collapsing P's skipped
        key.
        """
        seen_skip = False
        for key in product(*self.unique):
            skipped = any(atom is None for atom in key)
            if self.kind == "v" or not skipped:
                yield key
            elif self.kind == "p" and not seen_skip:
                seen_skip = True
                yield None

    def map_size(self):
        """Count unique keys without traversing the Cartesian product."""
        size = prod(map(len, self.valid))
        return size + int(self.kind == "p" and self.skipped)

    def mapped_value(self, key):
        """
        Preserve tuple-key validation and each element's missing-key
        policy.
        """
        self.validate_key(key)
        if key is None and self.kind == "p" and self.skipped:
            return None
        return self.value(key)

    def validate_key(self, key):
        """
        Check mapping membership without creating a symbolic scalar
        wrapper.
        """
        if key is None and self.kind == "p" and self.skipped:
            return
        if not self._contains_tuple(key):
            raise KeyError(key)
        if self.kind != "v" and any(atom is None for atom in key):
            raise KeyError(key)

    def _contains_tuple(self, key):
        """Check tuple arity and each axis without touching scalar records."""
        if not isinstance(key, tuple):
            hash(key)
            return False
        return len(key) == len(self.membership) and all(
            atom in axis for atom, axis in zip(key, self.membership)
        )


class SelectionValues(SequencePreview, MutableSequence):
    """
    Defer the legacy list, materializing it only for explicit container
    edits.
    """

    def __init__(self, selection):
        """
        Share immutable membership while retaining independent list edits.
        """
        self.selection, self.data = selection, None

    def __len__(self):
        """Count list slots, including repeated coordinates and gaps."""
        return self.selection.size if self.data is None else len(self.data)

    def __getitem__(self, position):
        """
        Scalar reads are lazy; explicit slices return ordinary detached
        lists.
        """
        if self.data is not None:
            return self.data[position]
        if isinstance(position, slice):
            return [self[n] for n in range(len(self))[position]]
        return self.selection.value(self.selection.key(position))

    def __iter__(self):
        """Stream Cartesian order without decoding each ordinal position.

        If a local edit materializes the list during traversal, resume at the
        same ordinal in that list. This preserves list-iterator behavior for
        insertions, deletion, replacement and extension between reads.
        """
        position = 0
        for key in product(*self.selection.axes):
            if self.data is not None:
                break
            yield self.selection.value(key)
            position += 1
        if self.data is not None:
            yield from islice(self.data, position, None)

    def _materialize(self):
        """
        Copy on first structural edit, matching the legacy permissive list.
        """
        if self.data is None:
            self.data = list(self)
        return self.data

    def __setitem__(self, position, value):
        """Keep raw list edits independent of the selection's map."""
        self._materialize()[position] = value

    def __delitem__(self, position):
        """Preserve legacy list deletion without changing the native owner."""
        del self._materialize()[position]

    def insert(self, position, value):
        """
        Preserve legacy local insertion without changing native membership.
        """
        self._materialize().insert(position, value)

    def copy(self):
        """Materialize a detached ordinary list on explicit request."""
        return list(self)

    def __eq__(self, other):
        """
        Retain list equality, including shared symbolic identity shortcuts.
        """
        return list(self) == (
            list(other) if isinstance(other, SelectionValues) else other
        )


class SelectionMap(MappingPreview, MutableMapping):
    """
    Defer the legacy dict and preserve its separate mutable-container
    policy.
    """

    def __init__(self, selection):
        """
        Share fixed membership while retaining independent dictionary
        edits.
        """
        self.selection, self.data = selection, None

    def __len__(self):
        """Count unique mapped keys, excluding T gaps and collapsing P gaps."""
        return (
            self.selection.map_size() if self.data is None else len(self.data)
        )

    def __iter__(self):
        """Traverse captured key order without creating symbolic members."""
        return self.selection.keys() if self.data is None else iter(self.data)

    def __getitem__(self, key):
        """
        Read one entry from the lazy mapping or its explicitly edited copy.
        """
        if self.data is not None:
            return self.data[key]
        return self.selection.mapped_value(key)

    def __contains__(self, key):
        """Membership checks never instantiate previously unseen symbols."""
        if self.data is not None:
            return key in self.data
        try:
            self.selection.validate_key(key)
        except KeyError:
            return False
        return True

    def freeze(self):
        """
        Capture map contents while sharing immutable unedited selection
        state.
        """
        return (
            SelectionMap(self.selection)
            if self.data is None
            else self.data.copy()
        )

    def _materialize(self):
        """Retain ordinary dict behavior after the first explicit map edit."""
        if self.data is None:
            self.data = dict(self.items())
        return self.data

    def __setitem__(self, key, value):
        """Keep legacy local dictionary writes independent of the list."""
        self._materialize()[key] = value

    def __delitem__(self, key):
        """Keep legacy local dictionary deletions independent of the list."""
        del self._materialize()[key]

    def copy(self):
        """Materialize an explicitly requested detached dictionary."""
        return dict(self.items())


def install(target, source, axes, kind):
    """Attach gap-aware facades without constructing per-coordinate objects."""
    selection = Selection(source, axes, kind)
    target._ = SelectionValues(selection)
    target.map = SelectionMap(selection)


def reselect(source, target, axes, kind):
    """
    Keep nested exceptional selections lazy and capture prior local edits.
    """
    mapping = source.map
    if not isinstance(mapping, SelectionMap):
        return False
    axes = axes_snapshot(axes)
    if kind != "v":
        _validate_axes(mapping, valid_axes(axes, kind))
    install(target, mapping.freeze(), axes, kind)
    return True


def _validate_axes(mapping, axes):
    """
    Validate rectangular membership by axis; replay only failures or edits.
    """
    if any(not axis for axis in axes):
        return
    membership = mapping.selection.membership
    if mapping.data is None and len(axes) == len(membership):
        if all(
            set(axis).issubset(allowed)
            for axis, allowed in zip(axes, membership)
        ):
            return
    for key in product(*axes):
        if key not in mapping:
            raise KeyError(key)
