"""Detached series retain coordinate identity independently of rendering."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from importlib import import_module
from numbers import Number
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Series:
    """One ordered profile and its original index and source metadata."""

    x: tuple
    values: tuple
    coordinates: tuple
    domain: tuple = ()
    key: tuple = ()
    label: str = ""
    panel: tuple = ()
    panel_label: str = ""
    xlabel: str = "Indices"
    n_sol: int | None = None
    lower: tuple | None = None
    upper: tuple | None = None
    xerr: Any = None
    yerr: Any = None
    source: Any = field(default=None, repr=False, compare=False)
    unit: str | None = None


@dataclass(frozen=True)
class Snapshot:
    """Detached values and complete coordinate keys for domain adapters."""

    coordinates: tuple
    values: tuple
    n_sol: int | None


def snapshot(source, *, n_sol=0):
    """Read an indexed quantity without declaring or evaluating variables.

    Coordinate order matches ``values``. Missing solution columns remain None;
    an unavailable solution raises ValueError. Downstream domain adapters can
    select these records and supply ``Series`` to the public chart functions.
    """
    values = values_of(source, n_sol)
    coordinates = (
        coordinate_keys(source)
        if hasattr(source, "map")
        else tuple(range(len(values)))
    )
    return Snapshot(
        coordinates, values, n_sol if hasattr(source, "output") else None
    )


def checks_enabled() -> bool:
    """Read the public switch at use time, including after composition."""
    return import_module("gana.plotting").CHECK_INDICES


def values_of(source, n_sol=0) -> tuple:
    """Read parameters or a selected variable history without evaluating it."""
    if not hasattr(source, "map"):
        return tuple(np.atleast_1d(source).tolist())
    if not hasattr(source, "output"):
        return tuple(source._)
    storage = getattr(source, "_symbol_storage", None)
    if storage is not None:
        return _native_values(storage, n_sol)
    members = [source] if source.parent is not None else source
    histories = [member.X for member in members]
    if not any(n_sol in history for history in histories):
        message = f"No stored solution {n_sol} for {source.name!r}"
        raise ValueError(message)
    return tuple(history.get(n_sol) for history in histories)


def _native_values(storage, number):
    """Read native histories without creating scalar wrappers or states."""
    owner = storage.owner
    snapshot = owner.__dict__.get("solution_values", {}).get(number)
    values = []
    found = snapshot is not None
    for position in range(len(storage.positions)):
        member_id = storage.positions.handle.id(position)
        history = owner.states.get(member_id, {}).get("X", {})
        column = storage.positions.handle.number(position)
        found = found or number in history
        value = (
            snapshot[column]
            if snapshot is not None and column < len(snapshot)
            else None
        )
        values.append(history.get(number, value))
    if not found:
        message = f"No stored solution {number} for {storage.root.name!r}"
        raise ValueError(message)
    return tuple(values)


def coordinate_keys(source) -> tuple:
    """Retain the exact scalar or selection keys in their declared order."""
    if getattr(source, "parent", None) is not None:
        return (tuple(source.index),)
    return tuple(source.map)


def _label(source):
    """
    Respect the existing explicit mathematical label without reparsing it.
    """
    latex = getattr(source, "ltx", None)
    return f"${latex}$" if latex else getattr(source, "name", "")


def _coordinate(atom):
    """Keep numeric coordinate spacing and descriptive category labels."""
    parents = getattr(atom, "parent", ())
    for parent, position in zip(parents, getattr(atom, "pos", ())):
        if parent.ordered:
            return parent.start + position
    name = getattr(atom, "name", atom)
    try:
        return float(name)
    except (ValueError, TypeError):
        return str(name)


def _dimension(source, selector, default, width):
    """Resolve a positional axis or an explicitly supplied index object."""
    if selector is False:
        return None
    if selector is None:
        return default if width > abs(default) - 1 else None
    if isinstance(selector, int):
        return range(width)[selector]
    axes = source.index
    if isinstance(axes, tuple):
        for position, axis in enumerate(axes):
            if axis is selector:
                return position
    message = "Axis selectors must be index objects or dimension positions"
    raise ValueError(message)


def _roles(source, keys, x, series, panel):
    width = len(keys[0])
    roles = [
        _dimension(source, x, -1, width),
        _dimension(source, series, -2, width),
        _dimension(source, panel, -3, width),
    ]
    normalized = tuple(None if r is None else r % width for r in roles)
    used = [r for r in normalized if r is not None]
    if len(set(used)) != len(used):
        message = "Each index dimension must have a distinct plotting role"
        raise ValueError(message)
    remaining = set(range(width)) - set(used)
    if any(len({id(key[r]) for key in keys}) > 1 for r in remaining):
        message = "Select remaining index dimensions before plotting"
        raise ValueError(message)
    return normalized


def _auxiliary(value, source, n_sol):
    if value is None:
        return None
    if hasattr(value, "map") and checks_enabled():
        actual = tuple(tuple(map(id, key)) for key in coordinate_keys(value))
        expected = tuple(
            tuple(map(id, key)) for key in coordinate_keys(source)
        )
        if actual != expected:
            message = "Bounds and coordinates must have matching indices"
            raise ValueError(message)
    return values_of(value, n_sol)


def _take(values, positions):
    if values is None:
        return None
    if len(values) == 1:
        return tuple(values[0] for _ in positions)
    return tuple(values[position] for position in positions)


def _copy_error(value):
    if value is None or isinstance(value, Number):
        return value
    return np.array(value, dtype=float, copy=True)


def _error(value, positions):
    if value is None or isinstance(value, Number):
        return value
    array = np.asarray(value, dtype=float)
    return array[..., positions].copy()


def extract(
    source,
    *,
    n_sol=0,
    x=None,
    series=None,
    panel=None,
    lower=None,
    upper=None,
    xerr=None,
    yerr=None,
    label=None,
):
    """Split an indexed quantity into x profiles, series and panels.

    The final dimension supplies x, the preceding dimension supplies series,
    and the third-last dimension supplies panels. Additional varying
    dimensions require a selection. Numerical arrays form one profile.
    """
    if isinstance(source, Series):
        return (
            _detached(
                source, x, series, panel, lower, upper, xerr, yerr, label
            ),
        )
    values = values_of(source, n_sol)
    if not hasattr(source, "map"):
        coordinates = tuple(range(len(values))) if x is None else tuple(x)
        return (
            Series(
                coordinates,
                values,
                coordinates,
                key=(id(source),),
                source=source,
                label=label or "",
                lower=_auxiliary(lower, source, n_sol),
                upper=_auxiliary(upper, source, n_sol),
                xerr=_copy_error(xerr),
                yerr=_copy_error(yerr),
            ),
        )
    keys = coordinate_keys(source)
    if not keys:
        message = "An indexed plot requires at least one coordinate"
        raise ValueError(message)
    x_values = _auxiliary(x, source, n_sol) if hasattr(x, "map") else None
    x_role = None if x_values is not None else x
    roles = _roles(source, keys, x_role, series, panel)
    bounds = (
        _auxiliary(lower, source, n_sol),
        _auxiliary(upper, source, n_sol),
    )
    return _profiles(
        source,
        values,
        keys,
        roles,
        bounds,
        x_values,
        x,
        (xerr, yerr),
        label,
        n_sol,
    )


def _group_positions(keys, roles):
    _, series, panel = roles
    groups: dict[tuple, list[int]] = {}
    for position, key in enumerate(keys):
        group = tuple(id(key[r]) for r in (panel, series) if r is not None)
        groups.setdefault(group, []).append(position)
    return groups.values()


def _series_label(source, first, series, label, n_sol):
    if label is not None:
        return label
    suffix = "" if series is None else f" ({first[series].name})"
    if hasattr(source, "output") and n_sol:
        suffix += f" [solution {n_sol}]"
    return _label(source) + suffix


def _series_key(source, first, series, n_sol):
    category = () if series is None else (id(first[series]),)
    return (id(getattr(source, "_owner_root", source)), n_sol, *category)


def _panel_info(first, panel):
    if panel is None:
        return (), ""
    return (id(first[panel]),), str(first[panel].name)


def _profiles(
    source,
    values,
    keys,
    roles,
    bounds,
    x_values,
    x_source,
    errors,
    label,
    n_sol,
):
    return tuple(
        _profile(
            source,
            values,
            keys,
            roles,
            bounds,
            x_values,
            x_source,
            errors,
            label,
            n_sol,
            positions,
        )
        for positions in _group_positions(keys, roles)
    )


def _profile(
    source,
    values,
    keys,
    roles,
    bounds,
    x_values,
    x_source,
    errors,
    label,
    n_sol,
    positions,
):
    horizontal, series, panel = roles
    first = keys[positions[0]]
    atoms = tuple(keys[i][horizontal] for i in positions)
    pkey, panel_label = _panel_info(first, panel)
    x = (
        _take(x_values, positions)
        if x_values is not None
        else tuple(_coordinate(atom) for atom in atoms)
    )
    return Series(
        x=x,
        values=tuple(values[i] for i in positions),
        coordinates=tuple(id(atom) for atom in atoms),
        domain=_domain(atoms, x_source, n_sol),
        source=source,
        key=_series_key(source, first, series, n_sol),
        label=_series_label(source, first, series, label, n_sol),
        panel=pkey,
        panel_label=panel_label,
        xlabel=_label(x_source) if x_values is not None else "Indices",
        n_sol=n_sol if hasattr(source, "output") else None,
        lower=_take(bounds[0], positions),
        upper=_take(bounds[1], positions),
        xerr=_error(errors[0], positions),
        yerr=_error(errors[1], positions),
    )


def _domain(atoms, x_source, n_sol):
    if hasattr(x_source, "map"):
        root = getattr(x_source, "_owner_root", x_source)
        return ("quantity", id(root), n_sol)
    return tuple(id(i) for i in getattr(atoms[0], "parent", ()))


def compatible(left: Series, right: Series, *, aligned=False):
    """Check domain meaning and, when required, exact coordinate ordering."""
    if left.domain != right.domain:
        message = "Incompatible x index domains; select matching indices"
        raise ValueError(message)
    if aligned and left.coordinates != right.coordinates:
        message = (
            "Grouped and stacked series require matching coordinate order"
        )
        raise ValueError(message)


def _series_bound(value, source):
    if isinstance(value, Series):
        if checks_enabled():
            compatible(source, value, aligned=True)
            if source.unit != value.unit:
                message = "Interval bounds require matching units"
                raise ValueError(message)
        return tuple(value.values)
    return None if value is None else tuple(np.atleast_1d(value).tolist())


def _series_axes(source, x, series, panel):
    """Resolve an optional value axis against the original coordinates."""
    if any(value is not None for value in (series, panel)) or (
        x is not None and not isinstance(x, Series)
    ):
        message = "Series already define x, series and panel coordinates"
        raise ValueError(message)
    if x is not None:
        if checks_enabled():
            compatible(source, x, aligned=True)
        source = replace(
            source,
            x=tuple(x.values),
            domain=("quantity", x.key),
            xlabel=x.label,
        )
    return source


def _detached(source, x, series, panel, lower, upper, xerr, yerr, label):
    """Copy adapter records while retaining their coordinate semantics."""
    bounds = {}
    for name, value in (("lower", lower), ("upper", upper)):
        selected = getattr(source, name) if value is None else value
        bounds[name] = _series_bound(selected, source)
    source = _series_axes(source, x, series, panel)
    return replace(
        source,
        x=tuple(source.x),
        values=tuple(source.values),
        coordinates=tuple(source.coordinates),
        domain=tuple(source.domain),
        key=tuple(source.key),
        panel=tuple(source.panel),
        label=source.label if label is None else label,
        xerr=_copy_error(source.xerr if xerr is None else xerr),
        yerr=_copy_error(source.yerr if yerr is None else yerr),
        **bounds,
    )
