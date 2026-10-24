"""Transient expression metadata for the existing plain and LaTeX formatters.

Rendering replays algebraic normalization, but never compiles coefficients or
births a collection of scalar F objects. Its context and memo belong to one
display call; neither the program nor a native expression retains them. Public
row access continues through the ordinary compatibility path.
"""

from collections.abc import Sized
from typing import cast

from ...sets.cases import Elem, FCase
from ...sets.function import F
from ...sets.rows import CompiledRows
from ...sets.variable import V
from .algebra import _DISPLAY, NativeRows, _replay

_PAIR_TERMS = 2


class _Formula(F):
    """
    An internal formatting shell with operand metadata and no public rows.
    """

    def __init__(self, *args, **kwargs):
        """
        The renderer explicitly initializes the shell before F returns it.
        """

    def __len__(self):
        """Use the validated batch size without requesting scalar members."""
        return self.__dict__.get("_display_size", 0)

    def handle_mismatch(self):
        """
        Record broadcast size; rendering does not need aligned row arrays.
        """
        # F.types has already resolved both operands to sized Gana values.
        left, right = (
            len(cast("Sized", self.one)),
            len(cast("Sized", self.two)),
        )
        self._display_size = max(left, right)
        self.mis = (
            0
            if left == right
            else (right // left if left < right else -left // right)
        )

    def _build_rows(self):
        """
        Keep only the metadata needed by distribution and objective display.
        """
        self._matrix_operands()
        self._display_has_members = any(
            _has_members(operand) for operand in (self.one, self.two)
        )

    def __call__(self, *key):
        """Selections retain the collection label, as CompiledRows does."""
        if not key or key == self.index:
            return self
        result = _compiled(self.name, self, len(self))
        result.index = (key,)
        return result

    def __getitem__(self, position):
        """Project only the scalar requested by an objective or short V sum."""
        if self.case == FCase.SUM:
            return _sum_member(self, position)
        row = _empty(_Formula)
        for name in (
            "one_type",
            "two_type",
            "mul",
            "add",
            "sub",
            "div",
            "rel",
            "case",
            "issumhow",
        ):
            setattr(row, name, getattr(self, name))
        row.parent, row.pos, row._display_size = self, position, 1
        row.n = self.__dict__.get("_display_number_start", 0) + position
        one = _member(self.one, position, len(self))
        row.one = one if one else None
        row.two = _member(self.two, position, len(self))
        row._matrix_operands()
        row.give_name()
        return row


class _CompiledFormula(_Formula, CompiledRows):
    """Reuse compiled selection/reduction formatting without compiled rows."""

    def _scale_by(self, parameter):
        """Compiled collections retain their undistributed product syntax."""
        return CompiledRows._scale_by(self, parameter)

    def __neg__(self):
        """Use the same coefficient scaling as a compiled collection."""
        return CompiledRows.__neg__(self)

    def latex(self):
        """Retain compact sum or selection output, including its font depth."""
        return CompiledRows.latex(self)

    @property
    def longname(self):
        """Compiled collections use their compact label as the long name."""
        return self.name


def _empty(kind):
    """Initialize one metadata shell with the existing empty F defaults."""
    result = object.__new__(kind)
    F.__init__(result)
    result.rhs_thetas = []
    return result


def _has_members(value):
    """Identify scalar-variable display without enumerating variable rows."""
    if isinstance(value, _Formula):
        return value.__dict__.get("_display_has_members", False)
    if isinstance(value, F):
        return any(v.parent is not None for v in value.variables)
    return isinstance(value, V) and value.parent is not None


def _member(value, position, size):
    """Follow consecutive-repeat broadcasting to a single existing operand."""
    member = value[position // (size // len(value))]
    if isinstance(value, V):
        return member(*member.index)
    return member


def _sum_member(source, position):
    """Mirror the scalar V-sum label selected by a one-row objective."""
    variable, over, axis = source.issumhow
    row = _empty(_Formula)
    row.case, row.parent = FCase.SUM, source
    row.issumhow = (variable[len(over) * position], over, axis)
    row._display_size = 1
    row.n = source.__dict__.get("_display_number_start", 0) + position
    row.give_name()
    return row


def _variable_pair(source, over, position, member):
    """Read a visible short-sum term without enumerating its other axis."""
    if position is None:
        return source[member]
    after = position + 1
    key = (*source.index[:position], over[member], *source.index[after:])
    return source(*key, make_new=True)


def _compiled(name, source, size):
    """Create compact collection metadata without maps or coefficient lists."""
    result = _empty(_CompiledFormula)
    result.name, result.one_type = name, Elem.F
    result._display_size = size
    result.variables = source.variables
    result.rhs_thetas = source.rhs_thetas
    result._display_has_members = bool(source.variables)
    result.index = source.index
    return result


def _scalar_number(source):
    """Honor the last registered selection sharing a one-row source.

    A valid nonempty selection of a one-row source can only repeat that row.
    The last occurrence owns its number, matching compatibility replay, without
    allocating coordinate maps or visiting unrelated arithmetic dependents.
    """
    pending, seen = [source], set()
    latest, number = -1, 0
    while pending:
        node = pending.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        start = node.__dict__.get("_native_number_start", -1)
        if len(node) and start > latest:
            latest, number = start, start + len(node) - 1
        pending.extend(
            child
            for child in node.__dict__.get("_native_dependents", {}).values()
            if child._native_recipe[0] == "select"
        )
    return number


class _Renderer:
    """
    Resolve each saved node once during one isolated formatting operation.
    """

    def __init__(self):
        """
        Keep temporary shells local, including reused expression operands.
        """
        self.memo = {}

    def binary(self, one=None, two=None, **options):
        """
        Reuse F normalization and formatting with row construction omitted.
        """
        result = object.__new__(_Formula)
        F.__init__(result, one, two, **options)
        return result

    def resolve(self, source):
        """Use authoritative exposed objects or replay immutable recipes."""
        if "_legacy_cache" in source.__dict__:
            return source._materialize()
        if id(source) not in self.memo:
            result = _replay(source._native_recipe)
            result._display_size = len(source)
            if len(source) == 1:
                result._display_number_start = _scalar_number(source)
            for name in ("n", "pname", "category"):
                if name in source.__dict__:
                    setattr(result, name, source.__dict__[name])
            self.memo[id(source)] = result
        return self.memo[id(source)]

    def objective(self, source):
        """
        Match O's scalar numeric display without exposing public row state.
        """
        return source if _has_members(source) else source[0]

    def sum(self, source, over=None, position=None):
        """Render expression sums compactly and preserve historical V sums."""
        if isinstance(source, NativeRows):
            source = self.resolve(source)
        if isinstance(source, V):
            return self._variable_sum(source, over, position)
        result = _compiled(f"sigma({source},{over})", source, 1)
        result.case, result.issumhow = FCase.SUM, (source, over, position)
        return result

    def _variable_sum(self, source, over, position):
        """
        Keep the two-term shortcut and compact larger-variable summations.
        """
        if over is None:
            length, over, position = len(source), source.index, None
        else:
            length = len(over)
            position = (
                source.index.index(over) if position is None else position
            )
        if length == _PAIR_TERMS:
            left = _variable_pair(source, over, position, 0)
            result = left + _variable_pair(source, over, position, 1)
        else:
            result = _empty(_Formula)
            result.case = FCase.SUM
            result.issumhow = (source.copy(), over, position)
            result.one, result.one_type = result, Elem.F
            result.variables = [source]
            result.give_name()
        result._row_layout = ()
        # Only expression normalization reads this private shell's index.
        # The visible sum label uses issumhow; no scalar coordinate map is
        # needed to concatenate it with another expression's metadata.
        if result.index is None:
            result.index = ()
        result._display_has_members = position is None
        return result


def render(source):
    """Build ephemeral display metadata and restore context even on failure."""
    renderer = _Renderer()
    token = _DISPLAY.set(renderer)
    try:
        return renderer.resolve(source)
    finally:
        _DISPLAY.reset(token)
