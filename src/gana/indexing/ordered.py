"""Lazy ordered index members and compact native axis identities.

Families retain concrete members once observed, preserving arbitrary mutable
metadata and identity. Structural list edits promote only that list; frozen
coordinate axes keep the original family and membership.
"""

from bisect import bisect_right
from collections.abc import Mapping, MutableSequence, Sequence
from weakref import ref


class OrderedFamily:
    """Freeze birth metadata and own only members that have been requested."""

    def __init__(self, root):
        """Capture names now, so later root renaming cannot rename children."""
        self.root = root
        self.name, self.start = str(root), root.start
        self.size = max(0, root.size)
        self.cache = {}

    def member(self, position):
        """Return one stable concrete I, with independent mutable metadata."""
        member = self.cache.get(position)
        if member is None:
            name = f"{self.name}[{self.start + position}]"
            member = self.root._ordered_member(position, name=name)
            member._ordered_origin = (ref(self), position)
            self.cache[position] = member
        return member

    def __setstate__(self, state):
        """Rebind weak provenance after copying a family and cached members."""
        self.__dict__.update(state)
        for position, member in self.cache.items():
            member._ordered_origin = (ref(self), position)


class OrderedAxis(Sequence):
    """Immutable membership snapshot sharing one ordered member family."""

    def __init__(self, family):
        """Keep birth membership independent of later raw index-list edits."""
        self.family = family

    def __len__(self):
        """Count members without creating them."""
        return self.family.size

    def __getitem__(self, position):
        """Resolve members; explicit slices return ordinary lists."""
        if isinstance(position, slice):
            return [self.family.member(n) for n in range(len(self))[position]]
        return self.family.member(range(len(self))[position])

    def __iter__(self):
        """Walk the frozen axis without normalizing every scalar position."""
        family = self.family
        return (family.member(position) for position in range(family.size))


class OrderedMembers(MutableSequence):
    """List-compatible ordered members, promoting on structural edits."""

    def __init__(self):
        """Start empty until the declaration is registered."""
        self.family = None
        self._list = []

    def birth(self, root):
        """Populate an empty declaration lazily after registration."""
        self.family = OrderedFamily(root)

    def snapshot(self):
        """Freeze untouched membership; edited lists use ordinary snapshots."""
        return OrderedAxis(self.family) if self.family else tuple(self._list)

    def _materialize(self):
        """Detach the editable list; existing axis snapshots stay fixed."""
        if self.family is not None:
            self._list = list(OrderedAxis(self.family))
            self.family = None
        return self._list

    def __len__(self):
        """Read current membership without creating individual indices."""
        return self.family.size if self.family else len(self._list)

    def __getitem__(self, position):
        """Read requested members, preserving negative and slice rules."""
        if self.family is not None:
            return OrderedAxis(self.family)[position]
        return self._list[position]

    def __iter__(self):
        """Read lazily while observing list edits between successive yields.

        Re-read the active storage on every step: an edit can materialize the
        list, and clearing then rebirthing can install a different family.
        Once exhausted, the generator stays exhausted like a list iterator.
        """
        position = 0
        while True:
            family = self.family
            if family is not None:
                if position >= family.size:
                    return
                member = family.member(position)
            else:
                if position >= len(self._list):
                    return
                member = self._list[position]
            # A suspended mutable iterator must not pin a detached family.
            del family
            yield member
            position += 1

    def __setitem__(self, position, value):
        """Preserve ordinary list replacement and extended-slice validation."""
        self._materialize()[position] = value

    def __delitem__(self, position):
        """Delete from this list without changing captured coordinate axes."""
        del self._materialize()[position]

    def insert(self, position, value):
        """Retain ordinary list insertion and clamping behavior."""
        self._materialize().insert(position, value)

    def __repr__(self):
        """Explicit representation has the same contents as a list."""
        return repr(list(self))

    def __eq__(self, other):
        """Keep list equality, including comparison with another lazy list."""
        return list(self) == (
            list(other) if isinstance(other, type(self)) else other
        )

    def copy(self):
        """Return an ordinary shallow list copy sharing concrete members."""
        return list(self)

    def __copy__(self):
        """Keep copy.copy equivalent to copying the original list."""
        return self.copy()

    def __add__(self, other):
        """Preserve list concatenation used by shifted indices."""
        return list(self) + other

    def __radd__(self, other):
        """Preserve reflected list concatenation for leading placeholders."""
        return other + list(self)

    def __mul__(self, count):
        """Repeat the list without duplicating member identities."""
        return list(self) * count

    __rmul__ = __mul__

    def __imul__(self, count):
        """Repeat this editable list while retaining its facade identity."""
        self._materialize().__imul__(count)
        return self

    def reverse(self):
        """Reverse membership with the same member objects as list.reverse."""
        self._materialize().reverse()

    def sort(self, *, key=None, reverse=False):
        """Delegate sorting and comparison errors to Python's list."""
        self._materialize().sort(key=key, reverse=reverse)


class OrderedAtoms(Sequence):
    """Address distinct ordered families without storing per-member objects."""

    def __init__(self, axes):
        """Assign one contiguous token interval per distinct member family."""
        self.families, self.ends = [], []
        self.offsets: dict[OrderedFamily, int] = {}
        size = 0
        for axis in axes:
            family = axis.family
            if family not in self.offsets:
                self.offsets[family] = size
                size += family.size
                self.families.append(family)
                self.ends.append(size)

    def __len__(self):
        """Count token slots without materializing their Python objects."""
        return self.ends[-1] if self.ends else 0

    def __getitem__(self, token):
        """Resolve one native token to its stable Python I identity."""
        if isinstance(token, slice):
            return [self[n] for n in range(len(self))[token]]
        token = range(len(self))[token]
        slot = bisect_right(self.ends, token)
        family = self.families[slot]
        return family.member(token - self.offsets[family])

    def __iter__(self):
        """Walk each token interval once, avoiding a bisect for every atom."""
        for family in self.families:
            yield from OrderedAxis(family)

    def encoded(self, axes):
        """Produce integer axes for native extraction without Python I rows."""
        return [
            range(self.offsets[a.family], self.offsets[a.family] + len(a))
            for a in axes
        ]


class OrderedTokens(Mapping):
    """Resolve observed index objects through immutable family provenance."""

    def __init__(self, atoms):
        """Share compact family intervals with the reverse token lookup."""
        self.atoms = atoms

    def __len__(self):
        """Count available tokens without constructing the indices."""
        return len(self.atoms)

    def __iter__(self):
        """Explicit key traversal materializes members as requested."""
        return iter(self.atoms)

    def __getitem__(self, atom):
        """Reject foreign identities even if their names or metadata match."""
        hash(atom)
        origin = getattr(atom, "_ordered_origin", None)
        if origin is not None:
            family, position = origin[0](), origin[1]
            if family in self.atoms.offsets:
                if family.cache.get(position) is atom:
                    return self.atoms.offsets[family] + position
        raise KeyError(atom)


def axis_snapshot(axis):
    """Keep untouched ordered axes lazy; snapshot other iterables normally."""
    values = getattr(axis, "_", None)
    return (
        values.snapshot()
        if isinstance(values, OrderedMembers)
        else tuple(axis)
    )
