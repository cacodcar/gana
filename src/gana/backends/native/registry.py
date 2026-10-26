"""Replace and number constraint spans without expanding other batches.

Public row mutations and unusual shared-row registries retain the established
identity-based list path. Replacement creates a new registry, preserving any
previously returned registry as a snapshot of its original members.
"""

from ...storage.symbols import SymbolRegistry
from .constraints import NativeConstraint


def _roots(registry):
    """Accept complete constraint spans with unchanged captured lengths."""
    if not isinstance(registry, SymbolRegistry):
        return None
    previous, roots = 0, []
    for (root, start), end in zip(registry.spans, registry.ends):
        if start or len(root) != end - previous:
            return None
        roots.append(root)
        previous = end
    return roots


def _deferred(root):
    """Identify batches whose row relations remain protected from edits."""
    return (
        isinstance(root, NativeConstraint)
        and "_legacy_cache" not in root.__dict__
    )


def _exposed_ids(root):
    """Inspect existing rows; uncreated scalars cannot have escaped aliases."""
    rows = (
        root.__dict__.get("_native_rows", {}).values()
        if _deferred(root)
        else root
    )
    return {id(row) for row in rows}


def _independent(roots, old):
    """Reject repeated owners and shared rows without exposing new scalars."""
    if len({id(root) for root in roots}) != len(roots):
        return False
    removed = _exposed_ids(old)
    return not any(
        removed.intersection(_exposed_ids(root))
        for root in roots
        if root is not old
    )


def replacement(registry, old, new):
    """Return a detached replacement when row identity is unambiguous.

    Repeated owners and shared rows use the legacy path, which removes all
    matching identities at their first occurrence. Inspecting existing IDs
    preserves that behavior without projecting untouched batches.
    """
    roots = _roots(registry)
    if roots is None or not any(root is old for root in roots):
        return None
    if not _independent(roots, old):
        return None
    result = SymbolRegistry()
    for root in roots:
        result.add(new if root is old else root)
    return result


def _matches(row, group):
    """Match Prg.cons order, including equality/nonnegativity overlap."""
    if group == 0:
        return row.leq and not row.nn
    return not row.leq if group == 1 else row.nn


def _number_group(roots, group, start):
    """Number lazy batches by offsets and edited rows by their relations."""
    for root in roots:
        if _deferred(root):
            if _matches(root, group):
                root._native_number_start = start
                start += len(root)
        else:
            for row in root:
                if _matches(row, group):
                    row.n = start
                    start += 1
    return start


def renumber(registry):
    """Preserve solver row order without allocating unrequested rows."""
    roots = _roots(registry)
    if roots is None:
        return False
    start = 0
    for group in range(3):
        start = _number_group(roots, group, start)
    return True
