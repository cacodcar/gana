"""
Python axis objects interned once; native tables own coordinate membership.
"""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from itertools import product
from numbers import Integral

from .ordered import OrderedAtoms, OrderedAxis, OrderedTokens
from .staging import CartesianMap


def _encode_bound(value):
    """Encode common built-ins directly, retaining numeric-subclass conversion.

    Exact type checks avoid abstract-number checks for each ordinary endpoint.
    Integer subclasses still pass through int(), preserving existing conversion
    behavior, and arbitrary-size integers never pass through a float.
    """
    if type(value) is int:
        return str(value), 0.0
    if type(value) is float:
        return "", value
    if isinstance(value, Integral):
        return str(int(value)), 0.0
    return "", float(value)


def encode_bounds(pair):
    """Encode a validated interval without rounding integer endpoints."""
    if pair is None:
        return None
    lower, upper = pair
    return _encode_bound(lower), _encode_bound(upper)


def encode_bounds_batch(bounds):
    """Prepare native endpoints, retaining subclass conversion order.

    Callers validate intervals first and consume this detached encoding before
    mutating native coordinates. The short-lived native buffer avoids Python
    endpoint tuples; no encoded result is cached across edits.
    """
    return import_module("gana._native").prepare_bounds(bounds, encode_bounds)


def decode_bounds(pair):
    """
    Rebuild integer endpoints after the native read lock has been released.
    """
    return tuple(int(text) if text else value for text, value in pair)


class CoordinateOwner:
    """
    Retain Python axis identities once, alongside one native coordinate table.
    """

    def __init__(self, keys, numbers, bounds):
        """Convert validated inputs before constructing native storage."""
        self.atoms: list | OrderedAtoms = []
        self.tokens: dict | OrderedTokens = {}
        encoded = self._intern(keys)
        self.handle = import_module("gana._native").MemberTable(
            encoded,
            numbers,
            bounds,
        )

    def _intern(self, keys):
        """
        Assign stable tokens to axis objects, preserving Python key equality.

        setdefault hashes each atom once, including new atoms. The next unused
        token identifies insertion without a second dictionary lookup. Equal
        keys retain the first Python atom and its existing native token.
        """
        atoms, tokens = self.atoms, self.tokens
        # Interning only runs on mutable buffers, including staged appends.
        if not isinstance(atoms, list) or not isinstance(tokens, dict):
            message = "Interning requires mutable coordinate buffers"
            raise TypeError(message)
        next_token = len(atoms)
        result = []
        for key in keys:
            row = []
            for atom in key:
                token = tokens.setdefault(atom, next_token)
                if token == next_token:
                    atoms.append(atom)
                    next_token += 1
                row.append(token)
            result.append(row)
        return result

    @classmethod
    def cartesian(cls, axes, numbers, bounds):
        """Intern axis atoms once and construct native rows without expansion.

        First occurrences follow product traversal: the first row, then each
        axis tail from right to left. Equal atoms on different axes retain
        their original representative identity.
        """
        owner = object.__new__(cls)
        if axes and all(isinstance(axis, OrderedAxis) for axis in axes):
            return cls._ordered_cartesian(axes, numbers, bounds)
        owner.atoms, owner.tokens = [], {}
        if all(axes):
            owner._intern([tuple(axis[0] for axis in axes)])
            owner._intern([axis[1:] for axis in reversed(axes)])
            encoded = owner._intern(axes)
        else:
            # An empty product never visits or hashes atoms on its other axes.
            encoded = [[] for _ in axes]
        owner.handle = import_module("gana._native").MemberTable.cartesian(
            encoded,
            numbers,
            bounds,
        )
        return owner

    @classmethod
    def _ordered_cartesian(cls, axes, numbers, bounds):
        """Keep ordered I members absent through native owner construction."""
        owner = object.__new__(cls)
        atoms = OrderedAtoms(axes)
        owner.atoms = atoms
        owner.tokens = OrderedTokens(owner.atoms)
        owner.handle = import_module("gana._native").MemberTable.cartesian(
            atoms.encoded(axes),
            numbers,
            bounds,
        )
        return owner

    def append(self, keys, numbers, bounds):
        """
        Stage new tokens separately; publish them after the native batch
        succeeds.
        """
        staged = object.__new__(CoordinateOwner)
        staged.atoms, staged.tokens = list(self.atoms), dict(self.tokens)
        encoded = staged._intern(keys)
        self.handle.append(encoded, numbers, bounds)
        self.atoms, self.tokens = staged.atoms, staged.tokens

    def __getstate__(self):
        """
        Serialize detached records and axis identities, excluding native locks.
        """
        return self.atoms, self.handle.export()

    def __setstate__(self, state):
        """
        Reconstruct native IDs in their original order and exact endpoint
        types.
        """
        self.atoms, records = state
        self.tokens = {atom: number for number, atom in enumerate(self.atoms)}
        keys, numbers, bounds = zip(*records) if records else ((), (), ())
        self.handle = import_module("gana._native").MemberTable(
            keys,
            numbers,
            bounds,
        )


class Positions(Mapping):
    """
    Ordered coordinate-to-local-position mapping over a shared native owner.
    """

    def __init__(self, owner, handle=None):
        """Root mappings are live; provided handles retain fixed membership."""
        self.owner = owner
        self.handle = owner.handle if handle is None else handle

    @classmethod
    def create(cls, keys, numbers=None, bounds=None):
        """
        Create the authoritative table for either numeric or symbolic members.
        """
        numbers = list(range(len(keys))) if numbers is None else numbers
        bounds = [None] * len(keys) if bounds is None else bounds
        if isinstance(keys, CartesianMap) and keys.compact:
            return cls(CoordinateOwner.cartesian(keys.axes, numbers, bounds))
        return cls(CoordinateOwner(keys, numbers, bounds))

    def __len__(self):
        """Count members without decoding coordinates."""
        return len(self.handle)

    def key(self, position):
        """Decode one tuple using the retained Python axis objects."""
        return tuple(
            self.owner.atoms[token] for token in self.handle.key(position)
        )

    def __iter__(self):
        """
        Traverse native insertion order without creating a coordinate
        dictionary.
        """
        return (self.key(position) for position in range(len(self)))

    def __getitem__(self, key):
        """
        Translate missing atoms or selection membership to ordinary KeyError.
        """
        if not isinstance(key, tuple):
            hash(key)  # Preserve TypeError for unhashable dictionary keys.
            raise KeyError(key)
        try:
            return self.handle.lookup(
                [self.owner.tokens[atom] for atom in key],
            )
        except (KeyError, IndexError) as error:
            raise KeyError(key) from error

    def resolve(self, keys):
        """
        Batch valid tuple coordinates; use ordinary lookup for precise errors.
        """
        try:
            encoded = [
                [self.owner.tokens[atom] for atom in key] for key in keys
            ]
            return self.handle.lookup_many(encoded)
        except (KeyError, IndexError, TypeError):
            return [self[key] for key in keys]

    def take(self, positions):
        """
        Share coordinates with a compact native fixed-membership selector.
        """
        return Positions(self.owner, self.handle.take(positions))

    def product(self, axes, *, allow_missing=False, last=False):
        """Resolve Cartesian axes without expanding Python coordinate tuples.

        Unknown atoms receive a token outside the owner's intern table so Rust
        can still accept an empty product and validate the complete request.
        Replay failed requests only to preserve the exact public KeyError.
        V can request None on a miss instead, avoiding an unused error replay.
        Expressions request the last duplicate, matching their legacy row map;
        member selection retains its existing first-occurrence semantics.
        """
        tokens = self.owner.tokens
        encoded = [
            [tokens.get(atom, len(tokens)) for atom in axis] for axis in axes
        ]
        try:
            handle, selector = self.handle.product(encoded, last=last)
        except IndexError:
            if allow_missing:
                return None
            for key in product(*axes):
                self[key]
            raise
        return Positions(self.owner, handle), selector

    def freeze(self):
        """
        Capture full membership in constant time without visiting coordinates.
        """
        return Positions(self.owner, self.handle.freeze())

    def __getstate__(self):
        """Preserve shared owner identity when pickling multiple selections."""
        ids = (
            None
            if self.handle is self.owner.handle
            else [self.handle.id(n) for n in range(len(self))]
        )
        return self.owner, ids

    def __setstate__(self, state):
        """
        Rebuild a live root or fixed selection against the restored owner.
        """
        self.owner, ids = state
        self.handle = (
            self.owner.handle if ids is None else self.owner.handle.take(ids)
        )
