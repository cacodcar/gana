"""Project individual constraint rows while deferring full bookkeeping.

Expression rows own their coefficient data and guard changes to those fields.
Constraint-specific edits promote the batch before mutation. Membership
metadata uses the established registration transaction.
"""

from importlib import import_module
from itertools import islice
from operator import index
from weakref import WeakValueDictionary

from ...sets.constraint import C
from .algebra import _DISPLAY
from .rows import _Dict, _List, projection_renderer, retain_projection
from .rows import _read as _expression_row
from .theta import has_thetas


class _Row(C):
    """A stable scalar C whose first structural edit restores ordinary rows."""

    def __getattribute__(self, name):
        """Keep numbering live and resolve membership only when requested."""
        state = object.__getattribute__(self, "__dict__")
        owner = state["_constraint_owner"]
        if name == "n":
            start = owner.__dict__.get("_native_number_start")
            return None if start is None else start + state["pos"]
        if name == "cons_by_pos" and owner._native_registered:
            return import_module("gana.backends.native.membership").positions(
                self,
            )
        value = object.__getattribute__(self, name)
        if name in state and type(value) in (list, dict):
            wrapper = _List if isinstance(value, list) else _Dict
            value = state[name] = wrapper(value, owner)
        return value

    def __setattr__(self, name, value):
        """Promote before replacing relation, row or bookkeeping metadata."""
        self.__dict__["_constraint_owner"]._materialize()
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        """Preserve compatibility semantics for explicit field deletion."""
        self.__dict__["_constraint_owner"]._materialize()
        object.__delattr__(self, name)

    def __reduce_ex__(self, protocol):
        """Serialize the ordinary graph, retaining aliases already exposed."""
        self.__dict__["_constraint_owner"]._materialize()
        return object.__reduce_ex__(self, protocol)


def _bind_theta(function):
    """Fill one registered row's theta columns without promoting its graph."""
    terms = function._theta_terms
    function.__dict__.update(
        F=[coefficient for _, _, coefficient in terms],
        Z=[owner.map[key].n for owner, key, _ in terms],
    )


def _watch(source, function):
    """Finish constraint binding before edits to a projected function row."""
    roots = (source.function, function.__dict__.get("_row_owner"))
    for root in roots:
        if root is not None:
            observers = root.__dict__.get("_native_constraint_observers")
            if observers is None:
                observers = WeakValueDictionary()
                root.__dict__["_native_constraint_observers"] = observers
            observers[id(source)] = source


def _function(source, position, renderer):
    """Share normalization without leaking context between requested rows."""
    token = _DISPLAY.set(renderer)
    try:
        return _expression_row(source.function, position, renderer)
    finally:
        _DISPLAY.reset(token)
        retain_projection(source.function, renderer)


def _read(source, position, renderer):
    """Build one scalar using C's existing initialization and F projection."""
    cache = source.__dict__.setdefault("_native_rows", {})
    if position not in cache:
        function = _function(source, position, renderer)
        # Operand replay can promote this constraint through its observers.
        # The old cache is then detached; return the adopted authoritative row.
        if "_legacy_cache" in source.__dict__:
            return source._legacy_cache[position]
        if source._native_registered and has_thetas(source.function):
            _bind_theta(function)
        row = C(
            function,
            leq=source.leq,
            nn=source.nn,
            parent=source,
            pos=position,
        )
        if "_legacy_cache" in source.__dict__:
            return source._legacy_cache[position]
        row.category = source.__dict__.get("_native_row_category", "General")
        row.__dict__["_constraint_owner"] = source
        row.__class__ = _Row
        cache[position] = row
        _watch(source, function)
    return cache[position]


def read(source, position):
    """Honor integer and slice indexing while retaining only requested rows."""
    positions = range(len(source))
    if not isinstance(position, slice):
        position = positions[index(position)]
        cache = source.__dict__.get("_native_rows")
        if cache is not None and position in cache:
            return cache[position]
    renderer = projection_renderer(source.function)
    if isinstance(position, slice):
        return [_read(source, p, renderer) for p in positions[position]]
    return _read(source, position, renderer)


def iterate(source):
    """Project incrementally; retain list-iterator edits after promotion."""
    position = 0
    renderer = projection_renderer(source.function)
    while True:
        if "_legacy_cache" in source.__dict__:
            yield from islice(iter(source._legacy_cache), position, None)
            return
        if position >= len(source):
            return
        yield _read(source, position, renderer)
        position += 1


def _adopt(row, replacement):
    """Preserve escaped constraint-owned containers during full replay."""
    state = replacement.__dict__.copy()
    state["cons_by_pos"] = row.__dict__["cons_by_pos"]
    for name in ("_", "args"):
        old = row.__dict__[name]
        if isinstance(old, _List):
            list.__setitem__(old, slice(None), [row])
            state[name] = old
        elif isinstance(old, _Dict):
            dict.clear(old)
            dict.update(old, state[name])
            state[name] = old
    current = row.__dict__
    current.clear()
    current.update(state)
    object.__setattr__(row, "__class__", C)
    list.__setitem__(row._, slice(None), [row])


def adopt(source):
    """Install already-exposed rows before rebuilding variable memberships."""
    for position, row in source.__dict__.pop("_native_rows", {}).items():
        _adopt(row, source._legacy_cache._[position])
        source._legacy_cache._[position] = row


def bindings(source):
    """Keep escaped theta arrays through replay and column binding."""
    return [
        (position, row.function, name, value)
        for position, row in source.__dict__.get("_native_rows", {}).items()
        for name in ("F", "Z")
        if isinstance(value := row.function.__dict__[name], _List)
    ]


def restore_bindings(source, saved):
    """Populate original arrays before a caller's pending mutation resumes."""
    collection = source._legacy_cache.function
    bound = source._native_registered and has_thetas(source.function)
    for position, function, name, values in saved:
        list.__setitem__(values, slice(None), function.__dict__[name])
        function.__dict__[name] = values
        if bound and collection.parent is None:
            collection.__dict__[name][position] = values
