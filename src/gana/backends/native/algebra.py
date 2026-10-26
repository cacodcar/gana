"""Bulk native affine operations with explicit, deferred Python compatibility.

Native rows capture numeric values and V/T membership when built.
Legacy scalar objects are created only when an API needs them; no global
expression cache is maintained. Unsupported numeric domains retain Python's
existing exact arithmetic and reduction behavior.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from importlib import import_module
from typing import TYPE_CHECKING, cast
from weakref import WeakValueDictionary

from ...indexing.coordinates import Positions
from ...operators.sigma import sigma
from ...sets.cases import Elem, FCase
from ...sets.function import F
from ...sets.index import I
from ...sets.objective import O
from ...sets.parameter import P
from ...sets.rows import _axis_position, row_layout
from ...sets.theta import T
from ...sets.variable import V
from ...storage.parameters import ParameterStorage
from .theta import anonymous_operand
from .theta import restore_operands as restore_theta_operands
from .theta import snapshot as theta_snapshot

if TYPE_CHECKING:
    from ..._native import AffineRows
    from ...storage.symbols import SymbolStorage
    from .render import _Renderer
    from .theta import PendingTheta

_LEGACY = ContextVar("gana_legacy_affine", default=False)
_DISPLAY: ContextVar[_Renderer | None] = ContextVar(
    "gana_affine_display",
    default=None,
)
_REPLAY_STATE: ContextVar[tuple[list, list] | None] = ContextVar(
    "gana_replay_state",
    default=None,
)
SOLUTION_REPLAY: ContextVar[tuple[int, tuple] | None] = ContextVar(
    "gana_solution_replay",
    default=None,
)


def _native():
    """Resolve the explicit backend lazily, after package imports complete."""
    return import_module("gana._native")


def _parameter_snapshot(parameter):
    """
    Capture values without decoding native coordinates or exporting scalars.
    """
    result = object.__new__(type(parameter))
    result.__dict__ = parameter.__dict__.copy()
    storage = parameter.__dict__.get("_native_storage")
    if storage is None:
        result._, result.map = list(parameter._), parameter.map.copy()
        return result
    handle = storage.handle
    if isinstance(handle, _native().NumericPayload):
        handle = handle.span(0, 1, len(handle))
    ParameterStorage(storage.positions.freeze(), (), handle=handle).install(
        result,
    )
    return result


def _operand(value):
    """
    Compile supported owners in one binding call; return None for fallback.
    """
    if isinstance(value, NativeRows):
        if not value._is_lazy():
            return None
        return value._native_batch, value._native_owners, value, Elem.F
    if isinstance(value, P):
        source = _parameter_snapshot(value)
        storage = source.__dict__.get("_native_storage")
        batch = (
            _native().AffineRows.numeric(storage.handle)
            if storage
            else _native().AffineRows.constants(list(source._))
        )
        return batch, (), source, Elem.P
    return _symbol_operand(value)


def _symbol_operand(value):
    """Capture stable symbol IDs; anonymous theta columns bind later."""
    if not isinstance(value, (V, T)):
        return None
    if isinstance(value, T) and not len(value):
        # Empty theta arithmetic retains its existing compatibility errors.
        return None
    if "_symbol_storage" not in value.__dict__:
        pending = (
            anonymous_operand(value, _native())
            if isinstance(value, T)
            else None
        )
        return (*pending, Elem.T) if pending is not None else None
    if isinstance(value, V):
        source = value.copy()
        # This copy freezes membership, not display syntax. Replay performs
        # the ordinary F snapshot, which adds the public copy's font wrapper.
        source._ltx = value._ltx
    else:
        source = theta_snapshot(value)
    storage = source.__dict__["_symbol_storage"]
    return (
        _native().AffineRows.variables(storage.positions.handle),
        (storage.owner,),
        source,
        Elem.V if isinstance(value, V) else Elem.T,
    )


def _merge_owners(left, right):
    """Assign slots by identity, never invoking symbolic equality."""
    owners = list(left)
    slots = {id(owner): n for n, owner in enumerate(owners)}
    right_slots = []
    for owner in right:
        if id(owner) not in slots:
            slots[id(owner)] = len(owners)
            owners.append(owner)
        right_slots.append(slots[id(owner)])
    return tuple(owners), list(range(len(left))), right_slots


def _domain(left, right):
    """
    Match ordinary F's longest-operand domain and symbolic tie preference.
    """
    if len(left[0]) > len(right[0]):
        return left[2]
    if len(right[0]) > len(left[0]) or left[3] == Elem.P:
        return right[2]
    return left[2]


def _make(batch, owners, recipe, domain):
    """
    Create an F-compatible handle without invoking the legacy constructor.
    """
    result = object.__new__(NativeRows)
    result._native_batch, result._native_owners = batch, owners
    result._native_recipe, result._native_domain = recipe, domain
    # Default row IDs depend on the replayed form (a root or a scalar row).
    # Registration can assign n directly without triggering compatibility.
    result.pname, result.category = "", ""
    result._register_dependencies()
    return result


def try_build(one=None, two=None, **options):
    """
    Dispatch ordinary affine roots; incompatible domains use the old path.
    """
    renderer = _DISPLAY.get()
    if renderer is not None:
        return renderer.binary(one, two, **options)
    if _LEGACY.get() or options.get("parent") is not None:
        return None
    operations = [name for name in ("add", "sub", "mul") if options.get(name)]
    if len(operations) != 1 or options.get("div") or options.get("issumhow"):
        return None
    try:
        return _build(one, two, operations[0], options)
    except OverflowError:
        # i128 overflow and nonrepresentable integers preserve Python behavior.
        return None


def _build(one, two, operation, options):
    """
    Combine compatible native operands after validating explicit type hints.
    """
    left, right = _operand(one), _operand(two)
    if left is None or right is None:
        return None
    if options.get("one_type") not in (None, left[3]):
        return None
    if options.get("two_type") not in (None, right[3]):
        return None
    if not left[1] and not right[1]:
        return None
    if operation == "mul" and Elem.P not in (left[3], right[3]):
        return None
    recipe = ("binary", left[2], right[2], options)
    left, right, operation = _theta_order(left, right, operation)
    owners, left_slots, right_slots = _merge_owners(left[1], right[1])
    batch = left[0].combine(right[0], left_slots, right_slots, operation)
    return _make(
        batch,
        owners,
        recipe,
        _domain(right, left) if operation == "rsub" else _domain(left, right),
    )


def _theta_order(left, right, operation):
    """Match F's theta normalization, including term encounter order."""
    if left[3] == Elem.T:
        if operation == "add":
            return right, left, operation
        if operation == "sub" and right[3] != Elem.T:
            operation = "rsub"
    return left, right, operation


def _layout(source):
    """
    Resolve reduction axes without constructing any scalar expression rows.
    """
    while isinstance(source, NativeRows):
        source = source._native_domain
    if isinstance(source, tuple):
        return source
    storage = source.__dict__.get("_symbol_storage") or source.__dict__.get(
        "_native_storage",
    )
    if storage is not None:
        return source.index, storage.positions
    return row_layout(source)


def _selection_layout(source):
    """Reuse frozen owner coordinates; intern derived domains only on demand.

    Reductions already produce unique output coordinates. Legacy parameter
    domains may contain repetitions, so retain their ordered occurrences when
    installing a native table. The cache belongs to this expression only.
    """
    axes, keys = _layout(source)
    if not isinstance(keys, Positions):
        unique = dict.fromkeys(keys)
        positions = Positions.create(tuple(unique))
        if len(unique) != len(keys):
            lookup = {key: n for n, key in enumerate(unique)}
            positions = positions.take([lookup[key] for key in keys])
        keys = positions
        source._native_domain = axes, keys
    return axes, keys


def _reduce(source, over, position):
    """Reduce whole batches in Rust; axis grouping only decodes coordinates."""
    batch = source._native_batch
    if over is None:
        if position is not None:
            message = "A reduction position requires an index"
            raise ValueError(message)
        return _sum_batch(batch), ((), ((),))
    axes, keys = _layout(source)
    axis = _axis_position(axes, over, position)
    groups: dict[tuple, list[int]] = {}
    after = axis + 1
    for n, key in enumerate(keys):
        remaining = key[:axis] + key[after:]
        groups.setdefault(remaining, []).append(n)
    return (
        _sum_batch(batch, list(groups.values())),
        (axes[:axis] + axes[after:], tuple(groups)),
    )


def _sum_batch(batch, groups=None):
    """Keep term reduction native and preserve Python's compensated offsets."""
    try:
        return batch.sum_all() if groups is None else batch.sum_groups(groups)
    except OverflowError:
        # The binding calls this interpreter's sum on numeric offsets only.
        return batch.sum_python(groups)


def try_sum(source, over=None, position=None):
    """Return a native reduction when numeric semantics are fully preserved."""
    renderer = _DISPLAY.get()
    if renderer is not None:
        return renderer.sum(source, over, position)
    if _LEGACY.get():
        return None
    if isinstance(source, V) and not _variable_reduction_supported(
        source,
        over,
        position,
    ):
        return None
    operand = _operand(source)
    if operand is None or operand[3] in (Elem.P, Elem.T):
        return None
    batch, owners, snapshot, _kind = operand
    holder = _make(batch, owners, (), snapshot)
    try:
        reduced, layout = _reduce(holder, over, position)
    except OverflowError:
        return None
    return _make(reduced, owners, ("sum", snapshot, over, position), layout)


def _variable_reduction_supported(source, over, position):
    """Retain V defaults for empty and repeated-axis reductions."""
    if not len(source):
        return False
    if over is None:
        return position is None
    if position is None:
        return sum(axis is over or axis == over for axis in source.index) == 1
    return True


def _legacy(value):
    """
    Materialize nested native nodes only inside explicit compatibility work.
    """
    if not isinstance(value, NativeRows):
        return value
    renderer = _DISPLAY.get()
    return renderer.resolve(value) if renderer else value._materialize()


def _replay(recipe):
    """
    Reproduce legacy display, indexing and scalar identity from snapshots.
    """
    operation, source, *rest = recipe
    if operation == "sum":
        return sigma(_legacy(source), *rest)
    if operation == "scale":
        return _legacy(source)._scale_by(rest[0])
    if operation == "negate":
        return -_legacy(source)
    if operation == "objective":
        renderer = _DISPLAY.get()
        value = _legacy(source)
        return renderer.objective(value) if renderer else O(value).function
    if operation == "select":
        return _legacy(source)(*rest[0])
    other, options = rest
    return restore_theta_operands(
        F(one=_legacy(source), two=_legacy(other), **options),
    )


@contextmanager
def _replay_scope():
    """Finish dependency replay before restoring shared registration numbers.

    Selections share scalar rows, so the last registered collection owns their
    final row numbers. Replay order depends on which object is exposed first;
    restore numbered collections in registration order after all pending
    descendants have captured their values. Context isolation keeps nested
    replay in the same transaction without retaining a global expression graph.
    """
    state = _REPLAY_STATE.get()
    if state is not None:
        yield state
        return
    pending: list[NativeRows] = []
    numbered: list[NativeRows] = []
    token = _REPLAY_STATE.set((pending, numbered))
    try:
        yield pending, numbered
        # Drain iteratively so observer chains do not consume Python frames.
        while pending:
            child = pending.pop()
            if not child.__dict__.get("_legacy_pending"):
                child._materialize()
        for collection in sorted(
            numbered,
            key=lambda item: item._native_number_start,
        ):
            collection._restore_row_metadata()
    finally:
        _REPLAY_STATE.reset(token)


class NativeRows(F):
    """An immutable compiled batch with legacy members available on demand."""

    _native_batch: AffineRows
    _native_owners: tuple[SymbolStorage | PendingTheta, ...]
    _native_recipe: tuple
    _native_domain: object
    _native_dependents: WeakValueDictionary[int, NativeRows]
    _legacy_cache: F

    def __init__(self, *args, **kwargs):
        """The F factory already initialized the returned native instance."""

    def __getattr__(self, name):
        """
        Defer compatibility data; absent display protocols must stay read-only.
        """
        hidden = ("_native", "_legacy", "__", "_repr_", "_ipython_")
        if name.startswith(hidden):
            raise AttributeError(name)
        if name in {"name", "n", "pname", "category"}:
            return getattr(self._display(), name)
        return getattr(self._materialize(), name)

    def _display(self):
        """
        Render private metadata, keeping exposed compatibility edits live.
        """
        if "_legacy_cache" in self.__dict__:
            return self._materialize()
        return import_module("gana.backends.native.render").render(self)

    def _materialize(self):
        """
        Retain scalar identities after the caller explicitly requests them.
        """
        if "_legacy_cache" not in self.__dict__:
            with _replay_scope() as (pending, numbered):
                self._replay_rows()
                pending.extend(
                    self.__dict__.pop("_native_dependents", {}).values(),
                )
                if "_native_number_start" in self.__dict__:
                    numbered.append(self)
        self._restore_root_metadata()
        self._finish_constraint_rows()
        return self._legacy_cache

    def _finish_constraint_rows(self):
        """Bind exposed constraints before applying a function edit."""
        observers = self.__dict__.pop("_native_constraint_observers", {})
        for constraint in tuple(observers.values()):
            if not constraint.__dict__.get("_legacy_pending"):
                constraint._materialize()

    def _replay_rows(self):
        """Create compatibility rows once with native dispatch disabled."""
        token = _LEGACY.set(True)
        display = _DISPLAY.set(None)
        self._legacy_pending = True
        try:
            self._legacy_cache = _replay(self._native_recipe)
            if "_native_rows" in self.__dict__:
                import_module("gana.backends.native.rows").adopt(self)
            self._restore_row_metadata()
            self._restore_solution_values()
        finally:
            self.__dict__.pop("_legacy_pending", None)
            _DISPLAY.reset(display)
            _LEGACY.reset(token)

    def _register_dependencies(self):
        """Keep weak replay notifications without retaining unused expressions.

        Existing descendants must capture their legacy coefficients before a
        caller can mutate this node's exposed rows. Weak values avoid an
        expression cache and do not keep discarded descendants alive.
        """
        for source in self._native_recipe[1:]:
            if isinstance(source, NativeRows):
                dependents = source.__dict__.get("_native_dependents")
                if dependents is None:
                    dependents = source._native_dependents = (
                        WeakValueDictionary()
                    )
                dependents[id(self)] = self

    def _restore_root_metadata(self):
        """Propagate registration labels, including changes after replay."""
        if self._native_recipe[0] == "objective":
            # The selected legacy root can be shared with a named expression.
            # Refresh its labels even when this objective was displayed before.
            self._native_recipe[1]._restore_root_metadata()
        for name in ("n", "pname", "category"):
            if name in self.__dict__:
                setattr(self._legacy_cache, name, self.__dict__[name])

    def _restore_solution_values(self):
        """Replay historical expression evaluation with captured solve values.

        Using the original expression tree preserves arithmetic order. Context
        isolation keeps later edits to scalar X dictionaries authoritative and
        prevents this historical replay from mutating their contents.
        """
        for number, values in self.__dict__.get(
            "_native_solution_values",
            {},
        ).items():
            token = SOLUTION_REPLAY.set((number, values))
            try:
                self._legacy_cache.solution(number)
            finally:
                SOLUTION_REPLAY.reset(token)

    def _restore_row_metadata(self):
        """Keep child-parent identity and row numbers after replay."""
        legacy = self._legacy_cache
        for position, row in enumerate(legacy):
            # Native batch materialization supplies populated scalar rows.
            row = cast("F", row)
            if row.parent is legacy:
                row.parent = self
            start = self.__dict__.get("_native_number_start")
            if start is not None:
                row.n = start + position

    def __len__(self):
        """
        Count native rows, honoring explicit edits after compatibility replay.
        """
        if "_legacy_cache" in self.__dict__:
            return len(self._legacy_cache)
        return len(self._native_batch)

    def __getitem__(self, position):
        """Read only requested scalar rows, retaining ordinary slice lists."""
        if "_legacy_cache" in self.__dict__:
            return self._materialize()[position]
        return import_module("gana.backends.native.rows").read(self, position)

    def __iter__(self):
        """Construct scalar rows incrementally as the caller consumes them."""
        if "_legacy_cache" in self.__dict__:
            return iter(self._materialize())
        return import_module("gana.backends.native.rows").iterate(self)

    def latex(self):
        """
        Reuse row-class formatting without exposing untouched Python rows.
        """
        return self._display().latex()

    @property
    def longname(self):
        """Preserve compiled selection labels instead of empty F operands."""
        return self._display().longname

    def _is_lazy(self):
        """Exposed shared scalar rows remain authoritative for all selections.

        A selection shares its source's mutable compatibility rows on replay.
        Once any selection exposes them, the original root is materialized;
        sibling views must also use those rows for subsequent operations.
        """
        root = self.__dict__.get("_native_selection_root", self)
        return (
            "_legacy_cache" not in self.__dict__
            and "_legacy_cache" not in root.__dict__
        )

    def __call__(self, *key):
        """Select native rows without constructing scalar expression members.

        Flat public indices use shared Rust rows. Historical grouped keys and
        exposed compatibility rows retain F's exact dispatch and identity.
        Native coordinate tables resolve axes into compact local selectors.
        """
        if not key:
            return self
        if not self._is_lazy() or not all(isinstance(axis, I) for axis in key):
            return F.__call__(self, *key)
        axes, coordinates = _selection_layout(self)
        if len(key) != len(axes):
            message = "Expression selection must match its output dimensions"
            raise ValueError(message)
        keys, positions = coordinates.product(key, last=True)
        result = _make(
            self._native_batch.select(positions),
            self._native_owners,
            ("select", self, key),
            (key, keys),
        )
        result._native_selection_root = self.__dict__.get(
            "_native_selection_root",
            self,
        )
        result._native_row_selector = positions
        return result

    def __neg__(self):
        """
        Negate compiled terms while retaining legacy display and
        simplification.
        """
        recipe = self._native_recipe
        if recipe[0] == "binary" and recipe[3].get("case") == FCase.NEGVAR:
            return recipe[2]
        result = self * -1
        if isinstance(result, NativeRows):
            result._native_recipe = ("negate", self)
        return result

    def _scale_by(self, parameter):
        """
        Scale in Rust while replaying Python's distributed display on demand.
        """
        result = F(one=parameter, two=self, mul=True)
        if isinstance(result, NativeRows):
            result._native_recipe = (
                "scale",
                self,
                _parameter_snapshot(parameter),
            )
        return result

    def __getstate__(self):
        """
        Serialize immutable data and owner references, never native handles.
        """
        if self.__dict__.get("_native_rows"):
            self._materialize()
        state = self.__dict__.copy()
        state.pop("_native_dependents", None)
        state.pop("_native_constraint_observers", None)
        state.pop("_legacy_pending", None)
        state.pop("_native_row_selector", None)
        state["_native_batch"] = self._native_batch.export()
        return state

    def __setstate__(self, state):
        """Restore rows against the deserialized shared Python owner graph."""
        state["_native_batch"] = _native().AffineRows(state["_native_batch"])
        self.__dict__.update(state)
        self._register_dependencies()


def initialize_objective(objective, function):
    """
    Capture a scalar objective and defer Python's scalar-row selection.

    Ordinary O sometimes selects function[0] for numeric display. Keep that
    choice lazy and local to the objective so other uses of the original
    expression retain their collection syntax and registration metadata.
    """
    objective.function = _make(
        function._native_batch,
        function._native_owners,
        ("objective", function),
        function._native_domain,
    )
    if "_native_selection_root" in function.__dict__:
        objective.function._native_selection_root = (
            function._native_selection_root
        )
    # If O retains a named collection, its labels belong to that collection.
    for name in ("pname", "category"):
        del objective.function.__dict__[name]
    objective._native_batch = function._native_batch
    objective._native_owners = function._native_owners
    objective.constant = function._native_batch.offset(0)
    objective._, objective.X = objective.function, None
    objective.n, objective.pname = None, None


def objective_links(objective, remove=False):
    """
    Register by owner; update only metadata that has already been created.
    """
    for slot, owner in enumerate(objective._native_owners):
        links = owner.__dict__.setdefault("objective_links", [])
        links[:] = [(item, n) for item, n in links if item is not objective]
        if not remove:
            links.append((objective, slot))
        _update_member_links(owner, objective, slot, remove)


def _update_member_links(owner, objective, slot, remove):
    """Refresh existing metadata without creating untouched member states."""
    for member_id, state in owner.states.items():
        state["min_by"][:] = [
            item for item in state["min_by"] if item is not objective
        ]
        if not remove and objective._native_batch.contains(slot, member_id):
            state["min_by"].append(objective)


def member_objectives(owner, member_id):
    """Initialize a newly requested member's active objective registrations."""
    return [
        objective
        for objective, slot in owner.__dict__.get("objective_links", ())
        if objective._native_batch.contains(slot, member_id)
    ]
