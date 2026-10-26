"""Theta ownership at the boundary of generic native affine batches.

Registered V and T members share the Rust term representation, but occupy
independent solver column spaces. Keep that distinction in owner metadata;
interval bounds remain with T and are never converted into numeric offsets.
"""

from ...indexing.coordinates import Positions
from ...sets.theta import T


class PendingTheta:
    """Share anonymous coordinates without owning bounds or solver numbers.

    The declaration remains editable until registration. Expressions pin its
    coordinate order; binding resolves that order against the accepted owner.
    This caches no expressions and allocates no scalar theta wrappers.
    """

    bound_positions: Positions

    def __init__(self, root, keys):
        """Capture member identity separately from future program columns."""
        self.root, self.keys = root, keys
        self.positions = Positions.create(keys)

    def column_table(self):
        """Resolve captured coordinates into the registered native owner."""
        if "bound_positions" in self.__dict__:
            return self.bound_positions.handle
        storage = self.root.__dict__["_symbol_storage"]
        positions = storage.positions
        if tuple(positions) == self.keys:
            self.bound_positions = positions.freeze()
        else:
            self.bound_positions = positions.take(
                [positions[key] for key in self.keys],
            )
        return self.bound_positions.handle


def anonymous_operand(source, native):
    """Compile anonymous roots and selections while keeping public payloads.

    Scalar wrappers and placeholder selections retain compatibility dispatch.
    A changed declaration gets a new coordinate snapshot; old expressions
    continue referencing their original coordinates.
    """
    if source.birthed or source.parent is not None:
        return None
    if any(value is None for value in source._):
        return None
    root = source._owner_root
    keys = tuple(root.map)
    owner = root.__dict__.get("_native_pending_owner")
    if owner is None or owner.keys != keys:
        owner = PendingTheta(root, keys)
        root.__dict__["_native_pending_owner"] = owner
    positions = owner.positions
    if source is not root:
        positions = positions.take([positions[key] for key in source.map])
    frozen = object.__new__(T)
    frozen.__dict__ = source.__dict__.copy()
    frozen._selection_owner = root
    frozen._native_theta_source = source
    frozen._, frozen.map = list(source._), source.map.copy()
    return native.AffineRows.variables(positions.handle), (owner,), frozen


def register_pending(program, function, *, constraint_name=None):
    """Register anonymous native owners after all foreign-owner checks pass.

    Validate every declaration before changing program registries. Resolve
    captured keys first too, so a removed coordinate cannot partially register
    a constraint or leave variable bookkeeping behind.
    """
    owners = function.__dict__.get("_native_owners", ())
    pending = [owner for owner in owners if isinstance(owner, PendingTheta)]
    if not pending:
        return
    _validate_pending(pending)
    for name, theta in _registration_plan(program, pending, constraint_name):
        program.add_theta(name, theta)


def _validate_pending(pending):
    """Check every bound and captured coordinate before any registration."""
    for owner in pending:
        if "_symbol_storage" in owner.root.__dict__:
            # Registered membership is append-only. Resolve captured keys
            # once, then reuse the fixed selection without rechecking bounds.
            owner.column_table()
            continue
        owner.root._validated_bounds()
        for key in owner.keys:
            if key not in owner.root.map:
                raise KeyError(key)


def _registration_plan(program, pending, constraint_name):
    """Reserve generated names, including the incoming constraint's name.

    The same root can have several coordinate snapshots. Register it once in
    encounter order, and reject collisions before mutating either registry.
    """
    roots = {
        id(owner.root): owner.root
        for owner in pending
        if not program._bound_here(owner.root)
    }
    if not roots:
        return ()
    names = [f"θ{program.n_theta_sets + n}" for n in range(len(roots))]
    occupied = set(program.names)
    if constraint_name is not None:
        occupied.add(constraint_name)
    for name in names:
        if name in occupied:
            message = f"The name {name} is already registered"
            raise ValueError(message)
    return zip(names, roots.values())


def column_tables(constraints):
    """Supply late column maps only for batches with anonymous coordinates."""
    result = [
        [
            owner.column_table() if isinstance(owner, PendingTheta) else None
            for owner in constraint.function._native_owners
        ]
        for constraint in constraints
    ]
    return result if any(any(row) for row in result) else None


def snapshot(source):
    """Freeze registered theta membership while retaining the interval owner.

    This is an internal expression operand, not a public T transformation.
    Bounds and member identity remain shared; later owner growth cannot add
    terms to a previously constructed expression.
    """
    result = object.__new__(T)
    result.__dict__ = source.__dict__.copy()
    result._selection_owner = source._owner_root
    result._native_theta_source = source
    source.__dict__["_symbol_storage"].select(result)
    return result


def restore_operands(function):
    """Expose original T operands after frozen membership has built the rows.

    Legacy F retains ``expression.two is theta`` while its compiled rows
    capture construction-time membership. Restore that public identity without
    adding later coordinates to the compiled snapshot.
    """
    for name in ("one", "two"):
        operand = getattr(function, name)
        if isinstance(operand, T):
            setattr(
                function,
                name,
                operand.__dict__.get("_native_theta_source", operand),
            )
    return function


def has_thetas(function):
    """Inspect native owners without requesting compatibility attributes."""
    return any(isinstance(owner.root, T) for owner in function._native_owners)


def variable_owners(function):
    """Keep variable bookkeeping separate from registered theta intervals."""
    return tuple(
        owner
        for owner in function._native_owners
        if not isinstance(owner.root, T)
    )


def owner_masks(constraints, *, theta):
    """Select one column space before Rust accumulates repeated columns."""
    return [
        [
            isinstance(owner.root, T) == theta
            for owner in c.function._native_owners
        ]
        for c in constraints
    ]


def bind_rows(constraint):
    """Restore RHS theta columns when registered compatibility rows are read.

    All referenced theta owners have been registered before this path runs,
    including anonymous declarations bound by register_pending.
    """
    function = constraint.function
    for row in constraint:
        terms = row.function._theta_terms
        row.function.F = [coefficient for _, _, coefficient in terms]
        row.function.Z = [owner.map[key].n for owner, key, _ in terms]
    if function.parent is None:
        function.F = [row.function.F for row in constraint]
        function.Z = [row.function.Z for row in constraint]
