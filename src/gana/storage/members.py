"""
Temporary scalar wrappers whose mutable state belongs to their native owner.
"""

from ..backends.native.algebra import SOLUTION_REPLAY, member_objectives
from ..backends.native.constraints import materialize_member_constraints
from ..backends.native.results import member_history
from ..indexing.coordinates import decode_bounds, encode_bounds
from ..sets.theta import T
from ..sets.variable import V
from .symbols import STRUCTURAL, SymbolMap, SymbolStorage, SymbolValues


class _Member:
    """
    Synthesize self-references so persistent state never pins its wrapper.
    """

    def __getattr__(self, name):
        """
        Build scalar compatibility containers only when explicitly requested.
        """
        if name == "elements" or (name == "variables" and isinstance(self, V)):
            return [self]
        if name in {"_", "map"}:
            owner = self._member_owner
            positions = owner.positions.take([self.pos])
            storage = SymbolStorage(self.parent, positions, owner)
            return SymbolValues(storage) if name == "_" else SymbolMap(storage)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        """
        Protect member identity while retaining ordinary mutable metadata.
        """
        if name in {"_", "map"}:
            raise TypeError(STRUCTURAL)
        object.__setattr__(self, name, value)

    @property
    def pos(self):
        """
        Stable owner-local ID, independent of growable native vector addresses.
        """
        return self._member_id

    @pos.setter
    def pos(self, _value):
        """Owner-local IDs cannot be reassigned through a scalar wrapper."""
        raise TypeError(STRUCTURAL)

    @property
    def n(self):
        """Resolve the authoritative native global model column number."""
        return self._member_owner.positions.handle.number(self.pos)

    @n.setter
    def n(self, _value):
        """
        Global model column IDs cannot be reassigned through a scalar wrapper.
        """
        raise TypeError(STRUCTURAL)

    @property
    def parent(self):
        """Keep the owner alive without retaining the program itself."""
        return self._member_owner.root

    @parent.setter
    def parent(self, _value):
        """A scalar wrapper cannot migrate to another owner."""
        raise TypeError(STRUCTURAL)

    def __setstate__(self, state):
        """
        Restore shared state; its owner rebuilds identity lookup after graph
        loading.
        """
        self.__dict__ = state


class NativeVariable(_Member, V):
    """
    A V-compatible wrapper created only when its stable member ID is read.
    """

    @property
    def X(self):
        """
        Expose mutable history, with an isolated view for deferred F replay.
        """
        replay = SOLUTION_REPLAY.get()
        if replay is not None:
            number, values = replay
            return {number: values[self.n]}
        return self.__dict__["X"]

    @X.setter
    def X(self, values):
        """Preserve explicit replacement of the public solution dictionary."""
        self.__dict__["X"] = values

    @property
    def cons_by(self):
        """
        Resolve only rows containing this member, retaining list
        identity.
        """
        materialize_member_constraints(self._member_owner, self)
        return self.__dict__["cons_by"]

    @cons_by.setter
    def cons_by(self, value):
        """Finish pending links before replacing an explicitly exposed list."""
        if "_member_owner" in self.__dict__:
            materialize_member_constraints(self._member_owner)
            self.__dict__["_cons_by_observed"] = True
        self.__dict__["cons_by"] = value


class NativeTheta(_Member, T):
    """
    A T-compatible wrapper retaining exact endpoint values and owner identity.
    """

    @property
    def lb(self):
        """
        Decode the authoritative lower endpoint without narrowing integers.
        """
        return decode_bounds(
            self._member_owner.positions.handle.bounds(self.pos),
        )[0]

    @lb.setter
    def lb(self, value):
        """Validate a complete interval before changing its lower endpoint."""
        self._write_bounds((value, self.ub))

    @property
    def ub(self):
        """
        Decode the authoritative upper endpoint without narrowing integers.
        """
        return decode_bounds(
            self._member_owner.positions.handle.bounds(self.pos),
        )[1]

    @ub.setter
    def ub(self, value):
        """Validate a complete interval before changing its upper endpoint."""
        self._write_bounds((self.lb, value))

    def _write_bounds(self, pair):
        """
        Commit exact endpoints after Python validation and conversion finish.
        """
        pair = self._bound_pair(pair)
        self._member_owner.positions.handle.set_bounds(
            self.pos,
            encode_bounds(pair),
        )


def make_member(owner, member_id):
    """
    Reuse persistent member metadata without retaining scalar self-cycles.
    """
    state = owner.states.get(member_id)
    root = owner.root
    kind = NativeVariable if isinstance(root, V) else NativeTheta
    if state is None:
        state = _initial_state(owner, member_id, kind)
        owner.states[member_id] = state
    member = object.__new__(kind)
    member.__dict__ = state
    return member


def _initial_state(owner, member_id, kind):
    """Reuse existing member initialization, removing wrapper-owning fields."""
    if kind is NativeVariable:
        return _variable_state(owner, member_id)
    root = owner.root
    handle = owner.positions.handle
    arguments = [
        owner.positions.key(member_id),
        member_id,
        handle.number(member_id),
    ]
    if kind is NativeTheta:
        arguments.append(decode_bounds(handle.bounds(member_id)))
    prototype = root._new_member(
        *arguments,
        template=owner.template(member_id),
    )
    state = prototype.__dict__
    for name in ("_", "map", "elements", "variables", "n", "pos", "parent"):
        state.pop(name, None)
    if kind is NativeTheta:
        state.pop("lb")
        state.pop("ub")
    state.update(_member_owner=owner, _member_id=member_id)
    return state


def _variable_state(owner, member_id):
    """Reuse validated V defaults while giving each member mutable metadata."""
    template = owner.template(member_id)
    if "variable_defaults" not in template:
        defaults = V(**template["args"]).__dict__
        for name in (
            "_",
            "map",
            "elements",
            "variables",
            "n",
            "pos",
            "parent",
        ):
            defaults.pop(name, None)
        template["variable_defaults"] = defaults
    state = template["variable_defaults"].copy()
    state.update(
        name=f"{template['name']}[{member_id}]",
        index=owner.positions.key(member_id),
        _member_owner=owner,
        _member_id=member_id,
        cons_by=[],
        min_by=member_objectives(owner, member_id),
        X=member_history(owner, member_id),
        P=[None],
        eval_funcs={},
        evaluation={},
    )
    return state
