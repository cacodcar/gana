"""Read individual compatibility rows without expanding their entire batch.

Rows retain ordinary mutable Python fields. Their first edit promotes the saved
graph through the established replay transaction, before the edit takes place.
This preserves arithmetic snapshots and selection aliases while read-only row
inspection allocates only the requested scalar operands.
"""

from __future__ import annotations

from itertools import islice
from operator import index
from typing import TYPE_CHECKING

from ...sets.cases import Elem, FCase
from ...sets.function import F
from ...sets.rows import CompiledRows
from ...sets.theta import T
from ...sets.variable import V
from .algebra import _DISPLAY, SOLUTION_REPLAY, _selection_layout
from .render import _CompiledFormula, _Formula, _Renderer

if TYPE_CHECKING:
    from .algebra import NativeRows


def _mutation(method):
    """
    Promote before invoking a mutator, including slice and in-place edits.
    """

    def mutate(self, *args, **kwargs):
        """
        Finish dependent snapshots before exposing the requested mutation.
        """
        self.owner._materialize()
        return method(self, *args, **kwargs)

    return mutate


class _List(list):
    """
    An ordinary list whose first write preserves its native graph snapshot.
    """

    def __init__(self, values, owner):
        """Keep the collection alive for aliases held without their row."""
        super().__init__(values)
        self.owner = owner

    def __reduce_ex__(self, protocol):
        """
        Restore a plain list after the owning graph's explicit serialization.
        """
        self.owner._materialize()
        return list, (list(self),)

    __setitem__ = _mutation(list.__setitem__)
    __delitem__ = _mutation(list.__delitem__)
    __iadd__ = _mutation(list.__iadd__)
    __imul__ = _mutation(list.__imul__)
    append = _mutation(list.append)
    extend = _mutation(list.extend)
    insert = _mutation(list.insert)
    pop = _mutation(list.pop)
    remove = _mutation(list.remove)
    clear = _mutation(list.clear)
    reverse = _mutation(list.reverse)
    sort = _mutation(list.sort)


class _Dict(dict):
    """
    A row dictionary with the same promotion boundary as coefficient lists.
    """

    def __init__(self, values, owner):
        """
        Preserve mapping behavior and retain the owning compatibility graph.
        """
        super().__init__(values)
        self.owner = owner

    def __reduce_ex__(self, protocol):
        """
        Keep serialization free of mutation callbacks and transient owners.
        """
        self.owner._materialize()
        return dict, (dict(self),)

    __setitem__ = _mutation(dict.__setitem__)
    __delitem__ = _mutation(dict.__delitem__)
    __ior__ = _mutation(dict.__ior__)
    update = _mutation(dict.update)
    setdefault = _mutation(dict.setdefault)
    pop = _mutation(dict.pop)
    popitem = _mutation(dict.popitem)
    clear = _mutation(dict.clear)


class _Row(F):
    """
    A scalar F that switches to ordinary F before its first explicit edit.
    """

    def __getattribute__(self, name):
        """Resolve live registration numbers without expanding shared views."""
        if name != "n" and _DISPLAY.get() is not None:
            return object.__getattribute__(self, name)
        state = object.__getattribute__(self, "__dict__")
        if name == "n":
            return _number(state["_row_owner"], state["pos"])
        value = object.__getattribute__(self, name)
        if name in state and isinstance(value, (list, dict)):
            return _mutable_field(state, name, value)
        return value

    def __setattr__(self, name, value):
        """Include scalar metadata replacement in the mutation boundary."""
        self.__dict__["_row_owner"]._materialize()
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        """Deleting public metadata has the same semantics as replacing it."""
        self.__dict__["_row_owner"]._materialize()
        object.__delattr__(self, name)

    def __reduce_ex__(self, protocol):
        """Serialize the ordinary graph, preserving aliases held by callers."""
        self.__dict__["_row_owner"]._materialize()
        return object.__reduce_ex__(self, protocol)

    @property
    def matrix(self):
        """Aggregate one scalar's columns without promoting the whole graph."""
        result = self._matrix
        if not result:
            for column, coefficient in zip(self.P, self.A):
                dict.__setitem__(
                    result,
                    column,
                    result.get(column, 0) + coefficient,
                )
        return result


class _CompiledRow(_Row, CompiledRows):
    """
    A deferred reduction row retaining CompiledRows evaluation and display.
    """


def _mutable_field(state, name, value):
    """Protect a container only when it escapes scalar projection.

    Internal coefficient compilation reads plain lists. Public access retains a
    single protected object, including the theta list shared across siblings.
    """
    shared_theta = name == "rhs_thetas" and state["_row_shared_theta"]
    # Already protected containers need no further ownership lookup. Shared
    # theta lists still resolve through the owner so sibling identities agree.
    if not shared_theta and type(value) not in (list, dict):
        return value
    owner = state["_row_owner"]
    shared = owner.__dict__.get("_native_shared", {})
    if shared_theta:
        value = shared[name]
    if _DISPLAY.get() is not None:
        return value
    if type(value) is list:
        value = _List(value, owner)
    elif type(value) is dict:
        value = _Dict(value, owner)
    state[name] = value
    if shared_theta:
        shared[name] = value
    return value


def _selector(source):
    """
    Restore a compact selector after unpickling without caching row objects.
    """
    if "_native_row_selector" not in source.__dict__:
        _, parent, key = source._native_recipe
        _, coordinates = _selection_layout(parent)
        source._native_row_selector = coordinates.product(key, last=True)[1]
    return source._native_row_selector


def _number(source, position):
    """
    Find the last registered overlapping selection in compact coordinates.
    """
    pending, seen = [(source, position)], set()
    latest, number = -1, 0
    while pending:
        node, local = pending.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        start = node.__dict__.get("_native_number_start", -1)
        if start > latest:
            latest, number = start, start + local
        pending.extend(_selected_children(node, local))
    return number


def _selected_children(source, position):
    """Visit only selection descendants that share this particular scalar."""
    for child in source.__dict__.get("_native_dependents", {}).values():
        if child._native_recipe[0] == "select":
            local = _selector(child).last(position)
            if local is not None:
                yield child, local


def _key(operand, position):
    """Read one coordinate from compact native storage or a staging mapping."""
    storage = operand.__dict__.get("_symbol_storage") or operand.__dict__.get(
        "_native_storage",
    )
    if storage is not None:
        return storage.positions.key(position)
    return next(islice(operand.map, position, None))


def _alignment(operand, size):
    """Resolve broadcast metadata once per temporary normalization shell."""
    length = len(operand)
    stride = size // length if length else 1
    expression = isinstance(operand, F)

    def read(position):
        """Keep scalar reads live while reusing the fixed broadcast layout."""
        position //= stride
        value = operand[position]
        return value, value.index if expression else _key(operand, position)

    return read


class _Rows(_Formula):
    """Temporary normalized metadata capable of building one real F row."""

    _row_source: NativeRows
    _row_renderer: _RowRenderer

    def _build_rows(self):
        """Capture normalized operands before restoring theta identity."""
        super()._build_rows()
        self._row_operands = self.one, self.two
        self._row_one = _alignment(self.one, len(self))
        self._row_two = _alignment(self.two, len(self))

    def __getitem__(self, position):
        """
        Reuse public rows for saved nodes; build transient intermediate rows.
        """
        source = self.__dict__.get("_row_source")
        if source is not None:
            return _read(source, position, self._row_renderer)
        return self.row(position)

    def row(self, position):
        """
        Reuse the existing scalar builder and compile only its two operands.
        """
        one, one_key = self._row_one(position)
        two, two_key = self._row_two(position)
        keys = (
            *(one_key if self.one_type == Elem.F else (one_key,)),
            *(two_key if self.two_type == Elem.F else (two_key,)),
        )
        self._row_values = self._combine_row(one, two)
        left = self._operand_theta_terms(self.one, self.one_type, one, one_key)
        right = self._operand_theta_terms(
            self.two,
            self.two_type,
            two,
            two_key,
        )
        scale = one if self.mul else (-1 if self.sub else 1)
        self._row_terms = [
            *left,
            *((t, key, scale * a) for t, key, a in right),
        ]
        if "_row_template" not in self.__dict__:
            self._row_template = self._scalar_template()
        return self._new_aligned_row(
            self._row_template,
            one,
            two,
            one_key,
            two_key,
            index=keys,
            position=position,
        )

    def _inherit_compiled_row(self, child, _position):
        """Attach locally compiled values without allocating sibling arrays."""
        child.A, child.B = self._row_values
        child._theta_terms = self._row_terms if self.rhs_thetas else ()
        child.rhs_thetas = self.rhs_thetas


class _RowRenderer(_Renderer):
    """Share temporary normalization shells across a slice or row iterator."""

    def binary(self, one=None, two=None, **options):
        """
        Initialize F normalization with only scalar row construction changed.
        """
        result = object.__new__(_Rows)
        F.__init__(result, one, two, **options)
        return result

    def resolve(self, source):
        """
        Associate saved native nodes with their transient normalized shell.
        """
        result = super().resolve(source)
        if isinstance(result, _CompiledFormula):
            result.__class__ = _SavedRows
        elif type(result) is _Formula and source._native_recipe[0] == "sum":
            # Variable-sum display shells lack scalar coordinates.
            # Nested algebra needs the actual projected reduction member.
            result.__class__ = _SumRows
        if isinstance(result, _Rows):
            result.one, result.two = result._row_operands
            result._row_source, result._row_renderer = source, self
        elif isinstance(result, (_SavedRows, _SumRows)):
            result._row_source, result._row_renderer = source, self
        return result


class _SavedRows(_CompiledFormula):
    """Normalize compiled views while resolving their actual rows on demand."""

    _row_source: NativeRows
    _row_renderer: _RowRenderer

    def __getitem__(self, position):
        """Follow shared selections or build just one reduction output row."""
        return _read(self._row_source, position, self._row_renderer)


class _SumRows(_Formula):
    """Retain variable-sum formatting while supplying real scalar operands."""

    _row_source: NativeRows
    _row_renderer: _RowRenderer

    def __getitem__(self, position):
        """
        Project the reduction's coordinates and terms for enclosing
        algebra.
        """
        return _read(self._row_source, position, self._row_renderer)


def _selection(source, position):
    """Map one selected occurrence to the last matching source coordinate."""
    return source._native_recipe[1], _selector(source).at(position)


def _freeze(row, source):
    """
    Protect public mutable fields while keeping F identity and containers.
    """
    # Ordinary binary rows share this list; reduction outputs own theirs.
    row._row_shared_theta = isinstance(row.parent, _Rows)
    row.parent = source
    if row._row_shared_theta:
        shared = source.__dict__.setdefault("_native_shared", {})
        row.rhs_thetas = shared.setdefault("rhs_thetas", row.rhs_thetas)
    row.__dict__["_row_owner"] = source
    row.__class__ = _CompiledRow if isinstance(row, CompiledRows) else _Row
    return row


def _read(source, position, renderer):
    """Return a cached scalar or build only the requested operand path."""
    if "_legacy_cache" in source.__dict__:
        return source._materialize()[position]
    if source._native_recipe[0] == "select":
        parent, original = _selection(source, position)
        return _read(parent, original, renderer)
    if source._native_recipe[0] == "objective":
        return _read(source._native_recipe[1], position, renderer)
    cache = source.__dict__.setdefault("_native_rows", {})
    if position not in cache:
        shell = renderer.resolve(source)
        if source._native_recipe[0] == "sum" and not isinstance(shell, _Rows):
            row = _sum_row(source, position, shell)
        elif isinstance(shell, _Rows):
            row = shell.row(position)
        else:
            return source._materialize()[position]
        _restore_history(source, row)
        cache[position] = _freeze(row, source)
    if len(cache) == len(source):
        # An enclosing expression can finish a previously partial operand.
        source.__dict__.pop("_native_row_renderer", None)
    return cache[position]


def _evaluation_copy(row, memo):
    """
    Clone only scalar operands so existing evaluators cannot promote rows.
    """
    if id(row) in memo:
        return memo[id(row)][1]
    kind = CompiledRows if isinstance(row, CompiledRows) else F
    copy = object.__new__(kind)
    copy.__dict__ = row.__dict__.copy()
    copy.X, copy.parent = {}, copy
    memo[id(row)] = row, copy
    for name in ("one", "two"):
        value = getattr(row, name)
        if isinstance(value, F):
            setattr(copy, name, _evaluation_copy(value, memo))
    return copy


def _restore_history(source, row):
    """
    Evaluate one row in its original arithmetic order at each saved solve.
    """
    history = source.__dict__.get("_native_solution_values", {})
    for number, values in history.items():
        memo: dict[int, tuple[F, F]] = {}
        copied = _evaluation_copy(row, memo)
        token = SOLUTION_REPLAY.set((number, values))
        try:
            copied.solution(number)
            for original, evaluated in memo.values():
                dict.update(original.X, evaluated.X)
        finally:
            SOLUTION_REPLAY.reset(token)


def _sum_terms(source, position, row):
    """
    Export only a requested reduction's terms with existing owner identities.
    """
    ids, coefficients, offset = source._native_batch.take([position]).export()[
        0
    ]
    row.variables, row.A, row._theta_terms = [], [], []
    for (slot, member, _), coefficient in zip(ids, coefficients):
        owner = source._native_owners[slot]
        if isinstance(owner.root, T):
            key = owner.positions.key(member)
            row._theta_terms.append((owner.root, key, -coefficient))
        else:
            row.variables.append(owner.member(member))
            row.A.append(coefficient)
    row.P = [variable.n for variable in row.variables]
    row.B = -offset
    row.rhs_thetas = list({id(t): t for t, _, _ in row._theta_terms}.values())


def _sum_row(source, position, shell):
    """Build one compact reduction row; its cost scales with its own terms."""
    _, operand, over, axis = source._native_recipe
    row = F() if isinstance(operand, V) else CompiledRows()
    _sum_terms(source, position, row)
    row.parent, row.pos, row.case = source, position, FCase.SUM
    row.one_type, row._ = Elem.F, [row]
    if isinstance(operand, V):
        _, over, axis = shell.issumhow
        length = len(operand) if axis is None else len(over)
        row.issumhow = (operand[length * position], over, axis)
        row.index = tuple(v.index for v in row.variables)
        row.one, row.B = row, []
        row.give_name()
    else:
        _, coordinates = _selection_layout(source)
        row.index = (coordinates.key(position),)
        row.issumhow, row.name = shell.issumhow, shell.name
    row.map[row.index] = row
    return row


def _projection_root(source):
    """Selections and objectives project their root's scalar owner."""
    while source._native_recipe[0] in {"select", "objective"}:
        source = source._native_recipe[1]
    return source


def projection_renderer(source):
    """Reuse normalization only for a partially consumed scalar owner."""
    root = _projection_root(source)
    renderer = root.__dict__.get("_native_row_renderer")
    return _RowRenderer() if renderer is None else renderer


def retain_projection(source, renderer):
    """Keep a repeated-read plan until consumption or mutable replay finishes.

    Unexposed expressions and first scalar reads retain no extra plan. This
    cache contains normalization metadata, not a second coefficient store;
    all public rows still belong to their single native expression owner.
    """
    root = _projection_root(source)
    if root.__dict__.get("_native_row_renderer") is renderer:
        # Completed reads and replay remove this entry at their ownership
        # boundary; a retained identical plan is still partially consumed.
        return
    count = len(root.__dict__.get("_native_rows", ()))
    if renderer.memo and 1 < count < len(root):
        root.__dict__["_native_row_renderer"] = renderer
    else:
        root.__dict__.pop("_native_row_renderer", None)


def read(source, position):
    """
    Honor Python integer/slice indexing without constructing untouched rows.
    """
    positions = range(len(source))
    if not isinstance(position, slice):
        position = positions[index(position)]
        cache = source.__dict__.get("_native_rows")
        if cache is not None and position in cache:
            return cache[position]
    renderer = projection_renderer(source)
    token = _DISPLAY.set(renderer)
    try:
        if isinstance(position, slice):
            return [_read(source, p, renderer) for p in positions[position]]
        return _read(source, position, renderer)
    finally:
        _DISPLAY.reset(token)
        retain_projection(source, renderer)


def iterate(source):
    """
    Reuse normalization during iteration without leaking context on yield.
    """
    renderer = projection_renderer(source)
    position = 0
    while position < len(source):
        token = _DISPLAY.set(renderer)
        try:
            row = _read(source, position, renderer)
        finally:
            _DISPLAY.reset(token)
            retain_projection(source, renderer)
        yield row
        position += 1


def _adopt(row, replacement):
    """
    Keep escaped row/container identities when full replay becomes necessary.
    """
    state = replacement.__dict__.copy()
    for name in ("one", "two"):
        if state.get(name) is replacement:
            state[name] = row
    for name, old in row.__dict__.items():
        if isinstance(old, _List) and name in state:
            list.__setitem__(old, slice(None), state[name])
            state[name] = old
        elif isinstance(old, _Dict) and name in state:
            if name != "_matrix":
                dict.clear(old)
                dict.update(old, state[name])
            state[name] = old
    row.__dict__.clear()
    row.__dict__.update(state)
    object.__setattr__(row, "__class__", type(replacement))
    list.__setitem__(row._, slice(None), [row])
    for key in row.map:
        dict.__setitem__(row.map, key, row)


def adopt(source):
    """Replace replayed rows with already exposed objects and shared arrays."""
    source.__dict__.pop("_native_row_renderer", None)
    cache = source.__dict__.pop("_native_rows", {})
    legacy = source._legacy_cache
    _adopt_shared(source, legacy)
    replacements = {}
    for position, row in cache.items():
        replacement = legacy._[position]
        replacements[id(replacement)] = row
        _adopt(row, replacement)
        legacy._[position] = row
        legacy.A[position], legacy.P[position] = row.A, row.P
        if legacy.__dict__.get("_theta_rows"):
            legacy._theta_rows[position] = row._theta_terms
    for key, value in tuple(legacy.map.items()):
        if id(value) in replacements:
            legacy.map[key] = replacements[id(value)]


def _adopt_shared(source, legacy):
    """
    Keep the single shared theta-owner list across projected and new rows.
    """
    for name, shared in source.__dict__.pop("_native_shared", {}).items():
        original = getattr(legacy, name)
        list.__setitem__(shared, slice(None), original)
        setattr(legacy, name, shared)
        for row in legacy:
            if getattr(row, name) is original:
                setattr(row, name, shared)
