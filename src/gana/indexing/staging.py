"""Compact, editable declaration maps before native owner registration.

Ordinary declarations need only axis snapshots and positional values. Public
map access materializes a dictionary once, preserving its views, insertion
order and editing behavior. Registration can consume untouched axes directly.
"""

from collections.abc import MutableMapping
from itertools import product
from math import prod

from .ordered import OrderedAxis, axis_snapshot


class CartesianMap(MutableMapping):
    """Defer Cartesian row tuples until a declaration's map is accessed."""

    def __init__(self, axes):
        """Snapshot axes and collapse equal coordinates in product order."""
        snapshot = tuple(axis_snapshot(axis) for axis in axes)
        self.axes = (
            tuple(_unique_axis(axis) for axis in snapshot)
            if all(snapshot)
            else snapshot
        )
        self._size = prod(map(len, self.axes))
        self._values = None
        self._mapping = None

    @property
    def compact(self):
        """Only untouched maps may bypass expanded coordinate validation."""
        return self._mapping is None

    def fill(self, values):
        """
        Retain an independent value buffer, so later raw edits are checked.
        """
        if self._mapping is None:
            self._values = list(values)
        else:
            self._mapping.update(zip(self._mapping, values))

    def staged_values(self):
        """Read aligned values without constructing coordinate tuples."""
        return [None] * self._size if self._values is None else self._values

    def _dict(self):
        """Materialize once; escaped dictionary views stay live thereafter."""
        if self.compact:
            self._mapping = dict(
                zip(product(*self.axes), self.staged_values()),
            )
            self._values = None
        return self._mapping

    def __len__(self):
        """Count compact coordinates without visiting the product."""
        return self._size if self._mapping is None else len(self._mapping)

    def __iter__(self):
        """Expose dictionary iteration, including size-change errors."""
        return iter(self._dict())

    def __getitem__(self, key):
        """Preserve dictionary lookup and unhashable-key errors."""
        return self._dict()[key]

    def __setitem__(self, key, value):
        """Allow arbitrary raw edits; registration validates the final map."""
        self._dict()[key] = value

    def __delitem__(self, key):
        """Retain dictionary deletion and reinsertion order."""
        del self._dict()[key]

    def __repr__(self):
        """
        Display the same coordinates and values as an ordinary dictionary.
        """
        return repr(self._dict())

    def __reversed__(self):
        """Traverse reverse insertion order."""
        return reversed(self._dict())

    def keys(self):
        """Return a live dictionary key view."""
        return self._dict().keys()

    def values(self):
        """Return a live dictionary value view."""
        return self._dict().values()

    def items(self):
        """Return a live dictionary item view."""
        return self._dict().items()

    def copy(self):
        """Return a detached ordinary dictionary."""
        return self._dict().copy()

    def __copy__(self):
        """Keep copy.copy independent, just like copying the original dict."""
        return self.copy()

    def popitem(self):
        """Remove the last inserted item, matching dict rather than Mapping."""
        return self._dict().popitem()

    def clear(self):
        """Keep previously escaped views synchronized with a cleared map."""
        self._dict().clear()

    def update(self, *args, **kwargs):
        """Preserve dict's iterable, mapping and keyword update conventions."""
        self._dict().update(*args, **kwargs)

    def __or__(self, other):
        """Return an ordinary dictionary union without mutating this map."""
        other = other._dict() if isinstance(other, CartesianMap) else other
        return self._dict() | other

    def __ror__(self, other):
        """Preserve reflected dictionary-union ordering."""
        return other | self._dict()

    def __ior__(self, other):
        """Apply dictionary union updates in place."""
        self._dict().__ior__(other)
        return self


def fill_map(mapping, values):
    """Fill positional declaration values without expanding compact keys."""
    if isinstance(mapping, CartesianMap):
        mapping.fill(values)
    else:
        mapping.update(zip(mapping, values))


def _unique_axis(axis):
    """Ordered family members are unique by identity without visiting them."""
    return (
        axis if isinstance(axis, OrderedAxis) else tuple(dict.fromkeys(axis))
    )
