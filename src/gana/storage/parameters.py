"""Development parameter adapter: one native payload, two Python facades.

Set GANA_BACKEND=rust-parameters before importing Gana. Unregistered
declarations
keep their legacy staging buffers. Coordinates remain Python objects in this
first integration; only numeric values and immutable versions live in Rust.
"""

from __future__ import annotations

import operator
import os
import weakref
from collections.abc import Iterator, MutableMapping, MutableSequence
from importlib import import_module
from typing import Any

from ..indexing import selection
from ..indexing.coordinates import Positions
from ..sets.cases import PCase
from ..utils._display import MappingPreview, SequencePreview

BACKEND = os.environ.get("GANA_BACKEND", "python")
if BACKEND not in {"python", "rust-parameters"}:
    message = f"Unknown GANA_BACKEND: {BACKEND}"
    raise ValueError(message)
if BACKEND == "rust-parameters":
    # An explicitly requested native run must fail when its extension is
    # absent.
    import_module("gana._native")

NATIVE = BACKEND == "rust-parameters"

_STRUCTURAL = (
    "Native parameter storage has fixed coordinates; assign P(...) through "
    "its program to resize or replace it"
)


class ParameterStorage:
    """Coordinate IDs and a shared native payload or immutable snapshot."""

    def __init__(self, keys, values, *, handle=None):
        """Accept validated staging values or an already captured snapshot."""
        self.positions = (
            keys if isinstance(keys, Positions) else Positions.create(keys)
        )
        native = import_module("gana._native")
        self.owner = native.NumericOwner(values) if handle is None else None
        self.handle = (
            self.owner.payload() if self.owner is not None else handle
        )
        self.root = None

    def __getstate__(self):
        """
        Serialize detached values and coordinates, never locks or addresses.
        """
        return list(self.positions), self.handle.values()

    def __setstate__(self, state):
        """Reconstruct an independent payload; P restores its weak callback."""
        keys, values = state
        self.positions = Positions.create(keys)
        self.owner = import_module("gana._native").NumericOwner(values)
        self.handle = self.owner.payload()
        self.root = None

    def install(self, parameter) -> None:
        """
        Attach synchronized facades without retaining the owning P strongly.
        """
        self.root = weakref.ref(parameter)
        object.__setattr__(parameter, "_native_storage", self)
        object.__setattr__(parameter, "_", ParameterValues(self))
        object.__setattr__(parameter, "map", ParameterMap(self))

    def write(self, positions, values) -> None:
        """Convert the entire batch before detachment, locking or mutation."""
        converted = [float(value) for value in values]
        native = import_module("gana._native")
        if not isinstance(self.handle, native.NumericPayload):
            handle = native.NumericPayload(self.handle.values())
            handle.set_many(positions, converted)
            self.handle = handle
        else:
            self.handle.set_many(positions, converted)
        self._refresh()

    def _refresh(self) -> None:
        """Refresh constant shortcuts only while these facades are current."""
        parameter = self.root() if self.root is not None else None
        if parameter is not None and parameter._native_storage is self:
            refresh_case(parameter)

    def select(self, keys):
        """
        Resolve coordinates once and pin the current immutable data
        version.
        """
        positions = self.positions.resolve(keys)
        handle = self.handle.take(positions)
        return ParameterStorage(
            self.positions.take(positions),
            (),
            handle=handle,
        )

    def product(self, axes):
        """
        Capture values and Cartesian membership without per-coordinate IDs.
        """
        positions, selector = self.positions.product(axes)
        return ParameterStorage(
            positions,
            (),
            handle=self.handle.select(selector),
        )

    def freeze(self):
        """
        Pin current values for lazy skipped-coordinate compatibility
        facades.
        """
        handle = self.handle
        native = import_module("gana._native")
        if isinstance(handle, native.NumericPayload):
            handle = handle.span(0, 1, len(handle))
        return ParameterStorage(self.positions.freeze(), (), handle=handle)


class ParameterValues(SequencePreview, MutableSequence):
    """List-compatible reads and atomic, length-preserving numeric writes."""

    def __init__(self, storage: ParameterStorage):
        """Retain the payload even after its program replaces the root data."""
        self.storage = storage

    def __len__(self) -> int:
        """Read fixed membership without materializing Python numbers."""
        return len(self.storage.handle)

    def __iter__(self) -> Iterator[float]:
        """Export a coherent detached batch for traversal."""
        return iter(self.storage.handle.values())

    def __getitem__(self, position):
        """Preserve negative positions and detached Python list slices."""
        if isinstance(position, slice):
            return list(self)[position]
        position = range(len(self))[operator.index(position)]
        return self.storage.handle.get(position)

    def __setitem__(self, position, value) -> None:
        """
        Reject resizing; validate all slice values before a single update.
        """
        if isinstance(position, slice):
            positions = list(range(len(self))[position])
            values = list(value)
            if len(positions) != len(values):
                raise TypeError(_STRUCTURAL)
        else:
            positions = [range(len(self))[operator.index(position)]]
            values = [value]
        self.storage.write(positions, values)

    def __delitem__(self, position) -> None:
        """Coordinate deletion must use the supported program mutation API."""
        raise TypeError(_STRUCTURAL)

    def insert(self, _position, _value) -> None:
        """Coordinate growth must use the supported program mutation API."""
        raise TypeError(_STRUCTURAL)

    def reverse(self) -> None:
        """Prevent raw reordering of coordinate-aligned values."""
        raise TypeError(_STRUCTURAL)

    def copy(self) -> list[float]:
        """Explicit copies are detached and freely mutable."""
        return list(self)

    def __eq__(self, other):
        """Retain ordinary list comparison for legacy buffer assertions."""
        if isinstance(other, ParameterValues):
            other = list(other)
        return list(self) == other


class ParameterMap(MappingPreview, MutableMapping):
    """Insertion-ordered coordinate mapping over the same numeric payload."""

    def __init__(self, storage: ParameterStorage):
        """Share coordinates and data with the sequence facade."""
        self.storage = storage

    def __len__(self) -> int:
        """Count coordinates without exporting values."""
        return len(self.storage.positions)

    def __iter__(self) -> Iterator[Any]:
        """Traverse coordinates in their registration order."""
        return iter(self.storage.positions)

    def __getitem__(self, key):
        """Resolve one stable ID; missing coordinates retain KeyError."""
        return self.storage.handle.get(self.storage.positions[key])

    def __setitem__(self, key, value) -> None:
        """Point writes update both facades through their common payload."""
        self.update({key: value})

    def __delitem__(self, key) -> None:
        """Raw deletion would break coordinate alignment."""
        raise TypeError(_STRUCTURAL)

    def update(self, *args, **kwargs) -> None:
        """
        Validate the full batch before committing; reject coordinate growth.
        """
        incoming = dict(*args, **kwargs)
        if any(key not in self.storage.positions for key in incoming):
            raise TypeError(_STRUCTURAL)
        positions = [self.storage.positions[key] for key in incoming]
        self.storage.write(positions, incoming.values())

    def copy(self) -> dict:
        """Export detached coordinates and values in one coherent batch."""
        return dict(zip(self, self.storage.handle.values()))


def select(source, target, axes):
    """
    Select native P values with compact axes and lazy skipped-coordinate
    slots.
    """
    if selection.reselect(source, target, axes, "p"):
        return True
    native = source.__dict__.get("_native_storage")
    if native is None:
        return False
    axes = selection.axes_snapshot(axes)
    if selection.has_placeholders(axes):
        # Validate real coordinates now, even though scalar values remain lazy.
        native.positions.product(selection.valid_axes(axes, "p"))
        selection.install(target, ParameterMap(native.freeze()), axes, "p")
    else:
        native.product(axes).install(target)
    return True


def register(parameter) -> None:
    """Copy validated staging values into Rust without redundant Python lists.

    Coordinates are consumed synchronously by Positions.create. NumericOwner
    extracts its own vector, so retaining the old staging list cannot mutate
    the installed payload. Lazy selection facades still need a sequence export.
    """
    if BACKEND == "rust-parameters":
        values = (
            parameter._ if isinstance(parameter._, list) else list(parameter._)
        )
        ParameterStorage(parameter.map, values).install(parameter)


def replace(parameter, mapping) -> None:
    """
    Replace a registered payload while retained old facades stay detached.
    """
    storage = getattr(parameter, "_native_storage", None)
    if storage is None:
        parameter.map = mapping
        parameter._ = list(mapping.values())
        return
    replacement = ParameterStorage(list(mapping), (), handle=storage.handle)
    # Root identity is stable; its payload changes. Allocate all Python
    # metadata
    # before committing so conversion failures cannot expose a partial update.
    storage.owner.replace(list(mapping.values()))
    replacement.owner = storage.owner
    replacement.handle = storage.owner.payload()
    replacement.install(parameter)
    storage.owner = None


def refresh_case(parameter) -> None:
    """
    Keep scalar shortcuts and printed names consistent with numeric writes.
    """
    old_name = parameter.name
    numeric = parameter.case in (PCase.NUM, PCase.NEGNUM, PCase.ZERO)
    values = list(parameter._) if numeric else []
    if numeric and values and all(value == values[0] for value in values):
        parameter._set_numeric_case(values[0])
    else:
        parameter.case = PCase.SET
        if numeric:
            parameter.name = parameter._registration_name
    if parameter._ltx == old_name.replace("_", r"\_"):
        parameter._ltx = ""
