"""Compile unit-price accounts into an MPLP's parametric objective."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from graphlib import TopologicalSorter
from typing import TYPE_CHECKING, cast

import numpy as np
from ppopt.mplp_program import MPLP_Program
from ppopt.utils.mpqp_utils import gen_cr_from_active_set
from scipy.sparse import csr_matrix

if TYPE_CHECKING:
    from ..sets.constraint import C
    from ..sets.theta import T
    from ..sets.variable import V
    from .program import Prg


@dataclass(frozen=True)
class UnitPrice:
    """One registered account equals scale times price times quantity."""

    quantity: int
    theta: int
    scale: float


def price_terms(
    account: V,
    quantity: V,
    price: T,
    multiplier: float,
    existing: dict[int, UnitPrice],
) -> dict[int, UnitPrice]:
    """Validate and stage the whole indexed declaration before registration."""
    if not math.isfinite(multiplier):
        message = "A price multiplier must be finite"
        raise ValueError(message)
    if len(account) != len(quantity) or len(price) not in (
        1,
        len(account),
    ):
        message = "Account, quantity and price dimensions do not match"
        raise ValueError(message)
    terms: dict[int, UnitPrice] = {}
    for i, (total, usage) in enumerate(zip(account, quantity)):
        theta = price[0 if len(price) == 1 else i]
        col = cast(int, total.n)
        term = UnitPrice(
            cast(int, usage.n), cast(int, cast("T", theta).n), multiplier
        )
        previous = terms.get(col, existing.get(col))
        if previous is not None and previous != term:
            message = "Account already has a different unit price"
            raise ValueError(message)
        terms[col] = term
    return terms


def _sum_row(row: C):
    """Recognize a homogeneous assignment of a positive sum to its LHS."""
    if not row.eq or row.B or any(row.F) or len(row.P) <= 1:
        return None
    target, *sources = cast("list[int]", row.P)
    lead, *coefficients = cast("list[float]", row.A)
    if lead <= 0 or target in sources or any(c >= 0 for c in coefficients):
        return None
    return target, [(s, -c / lead) for s, c in zip(sources, coefficients)]


def _dependent_sums(rows, prices):
    """Follow sums outwards from priced accounts, independent of row order."""
    by_source = defaultdict(list)
    for row in rows:
        assignment = _sum_row(row)
        if assignment is not None:
            target, terms = assignment
            for source, _ in terms:
                by_source[source].append((target, terms))
    queue = deque(prices)
    sums = {}
    while queue:
        for target, terms in by_source[queue.popleft()]:
            if target not in prices and target not in sums:
                sums[target] = terms
                queue.append(target)
    return sums


class PriceProjection:
    """Recover declared accounts from decisions and evaluated prices."""

    def __init__(self, program: Prg):
        prices = program.unit_prices
        sums = _dependent_sums(program.cons(), prices)
        self.decisions = [
            i
            for i in range(program.n_variables)
            if i not in prices and i not in sums
        ]
        positions = {v: i for i, v in enumerate(self.decisions)}
        if any(p.quantity not in positions for p in prices.values()):
            message = "A priced quantity cannot depend on another price"
            raise ValueError(message)
        self.quantities = [positions[p.quantity] for p in prices.values()]
        self.thetas = [p.theta for p in prices.values()]
        self.scales = np.array([p.scale for p in prices.values()])
        # The extra columns represent products theta * quantity. They are
        # bookkeeping coordinates, never independent solver decisions.
        basis = self.decisions + list(prices)
        self.lift = self._matrix(self._expand_sums(basis, sums), len(basis))

    @staticmethod
    def _expand_sums(basis, sums):
        """Express each aggregate in physical variables and price products."""
        weights = {v: {i: 1.0} for i, v in enumerate(basis)}
        dependencies = {v: [s for s, _ in terms] for v, terms in sums.items()}
        for target in TopologicalSorter(dependencies).static_order():
            if target in sums:
                expanded: dict[int, float] = defaultdict(float)
                for source, multiplier in sums[target]:
                    for col, value in weights[source].items():
                        expanded[col] += multiplier * value
                weights[target] = expanded
        return weights

    @staticmethod
    def _matrix(weights, width):
        data, rows, cols = [], [], []
        for row, terms in weights.items():
            for column, value in terms.items():
                rows.append(row)
                cols.append(column)
                data.append(value)
        return csr_matrix((data, (rows, cols)), shape=(len(weights), width))

    def split(self, matrix):
        """Split the projected coefficients into decisions and priced terms."""
        projected = matrix @ self.lift
        n = len(self.decisions)
        return projected[:, :n], projected[:, n:] * self.scales

    def products(self, coefficients):
        """Combine products with the same decision and theta."""
        terms: dict[tuple[int, int], float] = defaultdict(float)
        for i in np.flatnonzero(coefficients):
            terms[self.quantities[i], self.thetas[i]] += coefficients[i]
        return {key: value for key, value in terms.items() if value}

    def objective_matrix(self, products, n_thetas):
        """Accumulate repeated quantity/price pairs into the PPOPT H matrix."""
        matrix = np.zeros((len(self.decisions), n_thetas))
        np.add.at(matrix, (self.quantities, self.thetas), products)
        return matrix

    def recover(self, decisions, theta):
        """Evaluate each account before rounding the primal solution."""
        costs = (
            decisions[self.quantities, 0] * theta[self.thetas, 0] * self.scales
        )
        return self.lift @ np.vstack((decisions, costs[:, None]))


class PricedMPLP(MPLP_Program):
    """MPLP in physical coordinates with recovery of named variables."""

    def __init__(self, program: Prg):
        if program.active_objective is None:
            message = "Set an objective before compiling a price-parametric LP"
            raise ValueError(message)
        if any(v.bnr or v.itg for v in program.variables):
            message = "Price-parametric MPLP requires continuous decisions"
            raise ValueError(message)
        self.projection = PriceProjection(program)
        projection = self.projection
        n = program.n_variables
        nt = program.n_thetas
        rows = program.cons()
        A, products = projection.split(np.array(program.A).reshape((-1, n)))
        # A price may multiply a decision in the objective. A budget or other
        # constraint retaining that product needs a parameter-dependent A.
        for terms in products[np.any(products != 0, axis=1)]:
            if projection.products(terms):
                message = (
                    "A priced account creates a parameter-dependent "
                    "constraint matrix"
                )
                raise ValueError(message)
        b = np.asarray(program.B)
        F = np.array(program.F).reshape((-1, nt))
        keep = np.any(A != 0, axis=1)
        eq = np.array([row.eq for row in rows], dtype=bool)
        At, bt = self._parameter_domain(program, F[~keep], b[~keep], eq[~keep])
        bounds = self._nonnegative_rows(program)
        c, costs = projection.split(np.array(program.C).reshape((1, n)))
        super().__init__(
            A=np.vstack((A[keep], bounds)),
            b=np.concatenate((b[keep], np.zeros(len(bounds))))[:, None],
            c=c.T,
            H=projection.objective_matrix(costs[0], nt),
            A_t=At,
            b_t=bt[:, None],
            F=np.vstack(
                (
                    F[keep],
                    np.zeros((len(bounds), nt)),
                )
            ),
            c_c=np.array([[program.active_objective.constant]]),
            equality_indices=np.flatnonzero(eq[keep]).tolist(),
        )

    @staticmethod
    def _parameter_domain(program, F, b, equality):
        """Move pure-parameter constraints into the parameter domain."""
        varying = np.any(F != 0, axis=1)
        if np.any(~varying & ((b < 0) | (equality & (b != 0)))):
            message = (
                "Infeasible constant constraint after substituting prices"
            )
            raise ValueError(message)
        reverse = varying & equality
        A = np.vstack((program.CrA, -F[varying], F[reverse]))
        rhs = np.concatenate((program.CrB, b[varying], -b[reverse]))
        return A, rhs

    def equality_region(self):
        """Recover the unique feasible policy for an equality-determined LP.

        PPOPT's strict-complementarity test can be unbounded when there
        are no active inequalities. Full-rank equalities already determine
        the optimum wherever their primal policy is feasible.
        """
        active = self.equality_indices
        if len(active) == self.num_x() and self.check_feasibility(active):
            return gen_cr_from_active_set(self, active)
        return None

    def _nonnegative_rows(self, program):
        """Keep physical bounds and omit only provably nonnegative accounts."""
        projection = self.projection
        variables = program.variables
        physical, products = projection.split(
            np.array(program.NN).reshape((-1, len(variables)))
        )
        ordinary = ~np.any(products != 0, axis=1)
        nonnegative = np.array([variables[i].nn for i in projection.decisions])
        lower = np.array([t.lb for t in program.thetas])
        upper = np.array([t.ub for t in program.thetas])
        for i in np.flatnonzero(~ordinary):
            terms = projection.products(-products[i])
            if not terms:
                ordinary[i] = True
            else:
                self._check_nonnegative(
                    -physical[i], terms, nonnegative, lower, upper
                )
        return physical[ordinary]

    @staticmethod
    def _check_nonnegative(linear, terms, nonnegative, lower, upper):
        """Bound each physical coefficient over the parameter box."""
        minimum = linear.copy()
        free = bool(np.any(linear[~nonnegative]))
        for (quantity, theta), coefficient in terms.items():
            free |= not nonnegative[quantity]
            endpoint = lower[theta] if coefficient > 0 else upper[theta]
            minimum[quantity] += coefficient * endpoint
        if free or np.any(minimum < 0):
            message = (
                "Nonnegativity of a priced account depends on the price "
                "or the sign of its quantity"
            )
            raise ValueError(message)
