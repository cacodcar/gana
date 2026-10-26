"""Resolve variable/constraint links without expanding unrelated scalar rows.

One optional native index belongs to each queried constraint batch. Public
lists remain live across registration and replacement. Once a member's links
are resolved, edits to its list need no unrelated scalar rows.
"""

from .constraints import materialize_member_constraints


class _Links(list):
    """Resolved member links with ordinary local edits and guarded copying.

    The list is filled before escaping from ``read``. Later registration
    refreshes observed members, and each batch records which members it has
    linked. Replay therefore leaves explicit list edits authoritative without
    needing to construct unrelated rows when the edit occurs.
    """

    def __init__(self, values, storage):
        """Retain the shared symbol owner without a stored self-reference."""
        list.__init__(self, values)
        self.storage = storage

    def __reduce_ex__(self, protocol):
        """Complete graph aliases before copying an escaped membership list."""
        materialize_member_constraints(self.storage)
        # Memoize the empty copy before traversing rows that point back to it.
        return list, (), None, iter(self)


class _Positions(dict):
    """A resolved row's inverse links with local edits and graph-aware copying.

    All variables in the row have been linked before this mapping escapes.
    Replay adopts the same dictionary and skips those completed links, so edits
    remain authoritative without constructing other coordinates.
    """

    def __init__(self, values, owner):
        """Retain the constraint owner for explicit graph serialization."""
        super().__init__(values)
        self.owner = owner

    def __reduce_ex__(self, protocol):
        """Memoize the empty dictionary before copying cyclic row links."""
        self.owner._materialize()
        return dict, (), None, None, iter(self.items())


def read(member):
    """
    Expose one stable list and fill only matching rows in registration
    order.
    """
    state = member.__dict__
    owner = state["_member_owner"]
    if not state.get("_cons_by_observed"):
        state["cons_by"] = _Links(state["cons_by"], owner)
        state["_cons_by_observed"] = True
    for source in tuple(owner.__dict__.get("constraint_links", ())):
        link(source, member)
    return state["cons_by"]


def _positions(source, owner, member):
    """
    Build the optional native index once and export only matching
    positions.
    """
    state = source.__dict__
    if "_native_membership" not in state:
        state["_native_membership"] = (
            source.function._native_batch.membership()
        )
    slot = next(
        n
        for n, item in enumerate(source.function._native_owners)
        if item is owner
    )
    return state["_native_membership"].rows(slot, member)


def _append(values, row):
    """
    Use base-list append for internal links, retaining custom-list behavior.
    """
    if isinstance(values, _Links):
        list.append(values, row)
    else:
        values.append(row)


def link(source, member):
    """Populate all occurrences of one member exactly once for this batch."""
    if not source.function._is_lazy():
        source._materialize()
        return
    owner, position = member._member_owner, member.pos
    linked = source.__dict__.setdefault("_native_linked_members", set())
    key = owner, position
    if key in linked:
        return
    rows = [source[n] for n in _positions(source, owner, position)]
    if "_legacy_cache" in source.__dict__:
        # Projection observers already replayed every membership in this set.
        return
    values = member.__dict__["cons_by"]
    for row in rows:
        dict.__setitem__(row.__dict__["cons_by_pos"], member, len(values))
        _append(values, row)
    linked.add(key)


def positions(row):
    """Resolve inverse links once, retaining the live editable dictionary.

    Registration refreshes every observed member, and removal repairs inverse
    positions in place. Rewalking a resolved high-arity row on every lookup
    would repeat those same member queries quadratically during replacement.
    Structural row edits already promote the ordinary compatibility graph.
    """
    state = row.__dict__
    values = state["cons_by_pos"]
    if isinstance(values, _Positions):
        return values
    variables = {
        id(value): value for value in row.variables if value is not None
    }
    for variable in variables.values():
        read(variable)
    values = state["cons_by_pos"]
    owner = state.get("_constraint_owner")
    if type(values) is dict and owner is not None:
        values = state["cons_by_pos"] = _Positions(
            values,
            owner,
        )
    return values


def refresh(source):
    """
    Previously returned membership lists observe new constraint
    registration.
    """
    for owner in source._native_variable_owners:
        observed = [
            member
            for member, state in owner.states.items()
            if state.get("_cons_by_observed")
        ]
        for member in observed:
            link(source, owner.member(member))


def replay(source):
    """Append untouched memberships while retaining already projected links."""
    linked = source.__dict__.pop("_native_linked_members", set())
    for row in source._legacy_cache:
        variables = {
            id(value): value for value in row.variables if value is not None
        }
        for variable in variables.values():
            state = variable.__dict__
            key = state.get("_member_owner"), state.get("_member_id")
            if key not in linked:
                values = variable.cons_by
                row.cons_by_pos[variable] = len(values)
                _append(values, row)
    source.__dict__.pop("_native_membership", None)


def _remove(values, source):
    """
    Detach one set in place and repair positions without triggering
    projection.
    """
    retained = [row for row in values if row.parent is not source]
    if isinstance(values, _Links):
        list.__setitem__(values, slice(None), retained)
    else:
        values[:] = retained


def unregister(source):
    """Remove projected links without constructing unobserved member lists."""
    linked = source.__dict__.pop("_native_linked_members", set())
    for owner, member in linked:
        variable = owner.member(member)
        values = variable.__dict__["cons_by"]
        _remove(values, source)
        for position, row in enumerate(values):
            dict.__setitem__(row.__dict__["cons_by_pos"], variable, position)
    for row in source.__dict__.get("_native_rows", {}).values():
        dict.clear(row.__dict__["cons_by_pos"])
    source.__dict__.pop("_native_membership", None)
