"""Native constraint batches with deferred scalar bookkeeping and CSR export.

Individual scalar reads project just the requested expression and constraint.
Membership reads project only matching rows, and resolved list edits stay
local. Structural edits replay the compatibility representation; mutable
legacy rows remain authoritative after that replay.
There is no program-wide compilation cache.
"""

from contextvars import ContextVar
from importlib import import_module
from inspect import signature

from ...sets.cases import FCase
from ...sets.constraint import C
from .algebra import NativeRows
from .theta import (
    bind_rows,
    column_tables,
    has_thetas,
    owner_masks,
    variable_owners,
)

_CONSTRAINT_ARGUMENTS = signature(C.__init__)
_REGISTERING = ContextVar("gana_constraint_registration", default=False)


def supported(function, parent=None):
    """Only untouched native affine roots can defer scalar construction."""
    return (
        parent is None
        and isinstance(function, NativeRows)
        and function._is_lazy()
    )


def _negative_variable(function):
    """Recognize the legacy nonnegativity case without asking for F.case."""
    recipe = function._native_recipe
    return recipe[0] == "binary" and recipe[3].get("case") == FCase.NEGVAR


class NativeConstraint(C):
    """One owner for a batch; legacy C members are constructed on demand."""

    function: NativeRows

    def __init__(self, *args, **kwargs):
        """
        Validate the unchanged C signature before capturing batch metadata.
        """
        bound = _CONSTRAINT_ARGUMENTS.bind(self, *args, **kwargs)
        bound.apply_defaults()
        self._initialize(bound.arguments)

    def _initialize(self, options):
        """Capture relation metadata without accessing expression members."""
        function, leq, nn = (options[key] for key in ("function", "leq", "nn"))
        self.function = function
        self.leq, self.nn = leq, nn or (leq and _negative_variable(function))
        self.parent, self.pos = options["parent"], options["pos"]
        self.n, self.pname, self.category = None, None, options["category"]
        self.args = {"leq": leq, "nn": nn}
        self.binding, self.cons_by_pos = False, {}
        self._native_registered = False
        self._native_variable_owners = variable_owners(function)

    def __getattr__(self, name):
        """Replay compatibility fields while guarding incomplete unpickles."""
        if "function" not in self.__dict__ or name.startswith(
            ("_native", "_legacy", "__", "_repr_", "_ipython_"),
        ):
            raise AttributeError(name)
        return getattr(self._materialize(), name)

    def __len__(self):
        """Count rows without creating expression or variable wrappers."""
        return len(self.function)

    def __getitem__(self, position):
        """Project one row or a slice without filling untouched siblings."""
        if "_legacy_cache" in self.__dict__:
            return self._legacy_cache[position]
        return import_module("gana.backends.native.constraint_rows").read(
            self,
            position,
        )

    def __iter__(self):
        """Create rows incrementally while preserving their identities."""
        if "_legacy_cache" in self.__dict__:
            return iter(self._legacy_cache)
        return import_module("gana.backends.native.constraint_rows").iterate(
            self,
        )

    def __getstate__(self):
        """Finish an exposed graph before serializing aliases or row guards."""
        if self.__dict__.get("_native_rows") or self.__dict__.get(
            "_native_linked_members",
        ):
            # Even an empty query exposes owner lists. Finish before copying
            # this state so owner serialization cannot add unseen row aliases.
            self._materialize()
        state = self.__dict__.copy()
        state.pop("_native_membership", None)
        return state

    def _materialize(self):
        """
        Restore stable row identities, metadata and existing registrations.
        """
        if "_legacy_cache" not in self.__dict__:
            self._legacy_pending = True
            try:
                self._replay_rows()
            finally:
                self.__dict__.pop("_legacy_pending", None)
        return self._legacy_cache

    def _replay_rows(self):
        """Restore rows and bindings in one guarded transaction."""
        projected = import_module("gana.backends.native.constraint_rows")
        saved = projected.bindings(self)
        legacy = C(self.function._materialize(), leq=self.leq, nn=self.nn)
        self._legacy_cache = legacy
        start = self.__dict__.get("_native_number_start")
        for position, row in enumerate(legacy):
            row.parent = self
            row.category = self.__dict__.get("_native_row_category", "General")
            if start is not None:
                row.n = start + position
        projected.adopt(self)
        if self._native_registered:
            if has_thetas(self.function):
                bind_rows(legacy)
            self._register_legacy()
        projected.restore_bindings(self, saved)

    def _register_legacy(self):
        """
        Replay earlier links first, avoiding recursive later registrations.
        """
        token = _REGISTERING.set(True)
        try:
            self._materialize_predecessors()
            self._detach_links()
            import_module("gana.backends.native.membership").replay(self)
        finally:
            _REGISTERING.reset(token)

    def _materialize_predecessors(self):
        """
        Preserve cons_by insertion order across overlapping variable owners.
        """
        for owner in self._native_variable_owners:
            for item in tuple(owner.__dict__.get("constraint_links", ())):
                if item is self:
                    break
                item._materialize()

    def _detach_links(self):
        """Remove pending links before legacy registration can recurse."""
        for owner in self._native_variable_owners:
            links = owner.__dict__.get("constraint_links", [])
            links[:] = [item for item in links if item is not self]

    def update_variables(self):
        """
        Keep owner links until scalar metadata requires compatibility rows.
        """
        if self._native_registered and "_legacy_cache" not in self.__dict__:
            # Reusing a registered C retains legacy repeated-row bookkeeping.
            self._materialize()
        self._native_registered = True
        if "_legacy_cache" in self.__dict__:
            if has_thetas(self.function):
                bind_rows(self._legacy_cache)
            C.update_variables(self)
            return
        for owner in self._native_variable_owners:
            owner.__dict__.setdefault("constraint_links", []).append(self)
        # A previously returned cons_by list must observe new registrations.
        if self.__dict__.get("_native_rows"):
            self._materialize()
        elif any(owner.states for owner in self._native_variable_owners):
            import_module("gana.backends.native.membership").refresh(self)

    def unregister_variables(self):
        """
        Remove pending links or existing scalar registrations by identity.
        """
        self._detach_links()
        if "_legacy_cache" in self.__dict__:
            C.unregister_variables(self)
        elif self.__dict__.get("_native_linked_members"):
            import_module("gana.backends.native.membership").unregister(self)
        self._native_registered = False

    def categorize(self, category):
        """
        Defer propagation to rows unless they have already been requested.
        """
        self.category = category
        self._native_row_category = category
        if "_legacy_cache" in self.__dict__:
            C.categorize(self, category)
        for row in self.__dict__.get("_native_rows", {}).values():
            row.__dict__["category"] = category


def materialize_member_constraints(owner, member=None):
    """Resolve requested memberships, or finish owner bookkeeping for edits."""
    if _REGISTERING.get():
        return
    if member is not None:
        import_module("gana.backends.native.membership").read(member)
        return
    for constraint in tuple(owner.__dict__.get("constraint_links", ())):
        constraint._materialize()


def compile_program(program, *, theta=False):
    """Compile untouched native sets in the same order as Prg.cons().

    Legacy programs retain their established compiler. Integer overflow also
    requests that exact Python path; no integers are narrowed.
    """
    sets = program.constraint_sets
    if not all(_compilable(item) for item in sets):
        return None
    native = import_module("gana._native")
    ordered = _ordered_sets(sets)
    masks = owner_masks(ordered, theta=theta) if program.n_thetas else None
    columns = program.n_thetas if theta else len(program.variables)
    if theta and masks is None:
        masks = owner_masks(ordered, theta=True)
    try:
        return native.SparseRows(
            [item.function._native_batch for item in ordered],
            columns,
            owners=masks,
            negate=theta,
            column_tables=column_tables(ordered) if theta else None,
        )
    except OverflowError:
        return None


def _ordered_sets(sets):
    """Match inequalities, equalities and explicit nonnegativity row groups."""
    ordered = [item for item in sets if item.leq and not item.nn]
    ordered.extend(item for item in sets if not item.leq)
    ordered.extend(item for item in sets if item.nn)
    return ordered


def _compilable(constraint):
    """Any exposed scalar representation stays authoritative after replay."""
    return (
        isinstance(constraint, NativeConstraint)
        and "_legacy_cache" not in constraint.__dict__
        and constraint.function._is_lazy()
    )
