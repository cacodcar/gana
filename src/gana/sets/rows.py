"""Selection and reduction of compiled affine rows, preserving coordinates."""

from __future__ import annotations

from collections.abc import Sized
from itertools import product
from typing import cast

from gana.types import Number

from .cases import Elem, FCase
from .function import F
from .index import I


def row_layout(expression):
    """Return output axes and row coordinates independently of operand indices.

    Legacy F.index describes all operands. The longest operand supplies the
    output domain under Gana's consecutive-repeat broadcasting convention.
    Prefer symbolic operands to numerical coefficients when lengths tie.
    """
    if hasattr(expression, "_row_layout"):
        return expression._row_layout
    if not isinstance(expression, F):
        return expression.index, tuple(expression.map)
    if expression.parent is not None:
        axes, keys = row_layout(expression.parent)
        return axes, (keys[expression.pos],)
    operands = [
        (expression.one_type, expression.one),
        (expression.two_type, expression.two),
    ]
    candidates = [
        (kind, v)
        for kind, v in operands
        if v is not None and len(cast("Sized", v)) == len(expression)
    ]
    candidates.sort(key=lambda entry: entry[0] == Elem.P)
    if not candidates:
        message = "Expression has no unambiguous output domain"
        raise ValueError(message)
    return row_layout(candidates[0][1])


def _axis_position(axes, over, position):
    """
    Resolve a reduction axis, honoring explicit position zero and ambiguity.
    """
    matches = [
        n for n, axis in enumerate(axes) if axis is over or axis == over
    ]
    if position is None:
        if len(matches) != 1:
            message = (
                "Reduction index must identify exactly one expression axis"
            )
            raise ValueError(message)
        return matches[0]
    if position < 0 or position >= len(axes) or position not in matches:
        message = "Reduction position must match the supplied index"
        raise ValueError(message)
    return position


def _groups(expression, over, position):
    """
    Group existing rows by nonsummed coordinates, preserving encounter order.
    """
    if over is None:
        if position is not None:
            message = "A reduction position requires an index"
            raise ValueError(message)
        return (), {(): list(expression)}
    axes, keys = row_layout(expression)
    pos = _axis_position(axes, over, position)
    groups: dict[tuple, list[F]] = {}
    after = pos + 1
    for key, row in zip(keys, expression):
        remaining = key[:pos] + key[after:]
        groups.setdefault(remaining, []).append(row)
    return axes[:pos] + axes[after:], groups


class CompiledRows(F):
    """An affine row collection whose coefficients are already compiled.

    Arithmetic uses ordinary F nodes around the collection. Reductions do not
    build a recursive chain of additions or cache intermediate expressions.
    """

    def __neg__(self):
        """Negate compiled rows without traversing a reduction display node."""
        return self * -1

    def _scale_by(self, parameter):
        """
        Scale the compiled coefficients and constants without distribution.
        """
        return F(one=parameter, two=self, mul=True)

    @property
    def longname(self):
        """
        Use the compact reduction or selection label without self-recursion.
        """
        return self.name

    def latex(self):
        """Render a reduction from its source expression and selected axis."""
        if self.issumhow is None:
            return self.name
        source, over, _ = self.issumhow
        axis = "" if over is None else rf"_{{i \in {cast(I, over).ltx}}}"
        return rf"\sum{axis} \left({source.latex()}\right)"

    def _solution_value(self, n_sol):
        """
        Evaluate the actual row weights and offset, including nested sums.
        """
        return self.solution(n_sol)

    def solution(self, n_sol=0):
        """Evaluate compiled rows against solved variable values."""
        if self.parent is None:
            # Compiled collections contain populated scalar rows.
            return [cast("F", row).solution(n_sol) for row in self]
        if self._theta_terms:
            message = (
                "Evaluate parametric expressions with explicit theta values"
            )
            raise ValueError(message)
        coefficients = cast("list[Number]", self.A)
        self.X[n_sol] = sum(
            a * cast("Number", v.X[n_sol])
            for a, v in zip(coefficients, self.variables)
        ) - cast("Number", self.B)
        return self.X[n_sol]

    def eval(self, *values):
        """
        Evaluate one value per stored variable term, retaining the constant.
        """
        if self.parent is None:
            return [row.eval(*value) for row, value in zip(self, *values)]
        if self._theta_terms or len(values) != len(self.A):
            message = (
                "Evaluation requires one value per variable term and no thetas"
            )
            raise ValueError(message)
        return sum(a * value for a, value in zip(self.A, values)) - self.B


def collect_rows(rows, axes, keys, name):
    """Share scalar rows in an independently indexed expression container."""
    result = CompiledRows()
    result._, result.index = list(rows), (axes,)
    result._row_layout = axes, tuple(keys)
    result.map = {(key,): row for key, row in zip(keys, rows)}
    result.A = [row.A for row in rows]
    result.B = [row.B for row in rows]
    result.P = [row.P for row in rows]
    result._theta_rows = [row._theta_terms for row in rows]
    result.variables = [v for row in rows for v in row.variables]
    result.rhs_thetas = list(
        {
            id(t): t for row in rows for t in getattr(row, "rhs_thetas", ())
        }.values(),
    )
    result.mul_parameters, result.rhs_parameters = [], []
    result.one_type = Elem.F
    result.name = name
    return result


def _terms(rows, attribute):
    """Flatten one sparse term field without touching coefficient ownership."""
    return [term for row in rows for term in getattr(row, attribute)]


def _sum_row(rows):
    """Concatenate sparse terms and add constants once for a group of rows."""
    row = CompiledRows()
    row.variables = _terms(rows, "variables")
    row.P = [v.n for v in row.variables]
    row.A = _terms(rows, "A")
    row.B = sum(source.B or 0 for source in rows)
    row._theta_terms = _terms(rows, "_theta_terms")
    row.rhs_thetas = list(
        {id(owner): owner for owner, _, _ in row._theta_terms}.values(),
    )
    row.one_type = Elem.F
    row._ = [row]
    return row


def sum_expression(expression, over=None, position=None):
    """
    Reduce weighted affine rows over all coordinates or one explicit axis.
    """
    axes, groups = _groups(expression, over, position)
    rows = [_sum_row(group) for group in groups.values()]
    label = f"sigma({expression},{over})"
    result = collect_rows(rows, axes, tuple(groups), label)
    result.case = FCase.SUM
    result.issumhow = (expression, over, position)
    for n, (key, row) in enumerate(zip(groups, rows)):
        row.parent, row.pos, row.index = result, n, (key,)
        row.map[(key,)] = row
        row.case, row.issumhow, row.name = result.case, result.issumhow, label
    return result


def select_expression(expression, key):
    """
    Select compiled rows by output coordinates, retaining requested order.
    """
    # Accept both F's historical grouped key and the ordinary E(*indices) form.
    if len(key) == 1 and isinstance(key[0], tuple):
        key = key[0]
    if not all(isinstance(axis, I) for axis in key):
        message = "Expression selection requires one index per output axis"
        raise TypeError(message)
    axes, coordinates = row_layout(expression)
    if len(key) != len(axes):
        message = "Expression selection must match its output dimensions"
        raise ValueError(message)
    lookup = dict(zip(coordinates, expression))
    keys = tuple(product(*key))
    rows = [lookup[coordinate] for coordinate in keys]
    return collect_rows(rows, key, keys, expression.name)
