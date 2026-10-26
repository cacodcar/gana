"""Bulk solution histories and lightweight output records for native owners."""

from ...sets.variable import V
from ...storage.symbols import SymbolRegistry
from .export import owner_members


def load(program, snapshot, values, objective):
    """
    Validate first, then share one immutable value snapshot across owners.
    """
    solution = snapshot.normalize(values)
    if any(type(solution[n]) not in (int, float) for n in snapshot.referenced):
        return False
    number = program.n_solutions
    captured = tuple(solution)
    program.X[number] = solution
    owners = {
        id(root._symbol_storage.owner): root._symbol_storage.owner
        for root, _ in program.variables.spans
    }
    for owner in owners.values():
        _store_owner(owner, number, captured)
    for constraint in program.constraint_sets:
        constraint.function.__dict__.setdefault("_native_solution_values", {})[
            number
        ] = captured
    if program.active_objective is not None:
        program.active_objective.X = objective
    return True


def _store_owner(owner, number, values):
    """
    Keep existing X dictionaries live while leaving unseen members unborn.
    """
    owner.__dict__.setdefault("solution_values", {})[number] = values
    for position, state in owner.states.items():
        state["X"][number] = values[owner.positions.handle.number(position)]


def member_history(owner, position):
    """
    Detach a scalar dictionary lazily, omitting solves before its declaration.
    """
    column = owner.positions.handle.number(position)
    return {
        number: values[column]
        for number, values in owner.__dict__.get("solution_values", {}).items()
        if column < len(values)
    }


class _SolutionColumn:
    """
    An ephemeral formatting adapter, with no symbolic state or bookkeeping.
    """

    def __init__(self, owner, position, number):
        """Capture the same fields a newly created scalar would expose."""
        self.parent, self.pos = owner.root, position
        self.n = owner.positions.handle.number(position)
        self.index = owner.positions.key(position)
        self.ltx = owner.template(position)["args"]["ltx"]
        history = owner.__dict__.get("solution_values", {})
        self.X = {number: history[number][self.n]} if number in history else {}

    @property
    def index_ltx(self):
        """Reuse the public index formatter without constructing a V object."""
        descriptor = V.__dict__["index_ltx"]
        return descriptor.fget(self)

    def latex(self):
        """Reuse the established variable formula and escaping behavior."""
        formatter = V.__dict__["latex"]
        return formatter(self)


def update_solution(solution, registry, number):
    """
    Fill existing output dictionaries without allocating unseen member states.
    """
    if not isinstance(registry, SymbolRegistry):
        return False
    if any(
        "_symbol_storage" not in root.__dict__ for root, _ in registry.spans
    ):
        return False
    for owner, position in owner_members(registry):
        if position in owner.states:
            column = owner.member(position)
        else:
            column = _SolutionColumn(owner, position, number)
        solution._add_variable(column, number)
    return True
