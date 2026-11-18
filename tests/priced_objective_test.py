"""Unit prices in the MPLP objective and in the reported cost accounts."""

import numpy as np
import pytest

from src.gana import I, Prg, T, V, inf, sigma, sup


def suppliers():
    """Two substitutes for a total demand of two, with one uncertain price."""
    p = Prg()
    p.i = I(size=2)
    p.x = V(p.i)
    p.cost = V()
    p.price = T(_=(7.86, 8.89))
    p.add_price(p.cost, p.x[0], p.price)
    p.demand = sigma(p.x) == 2
    p.obj_min = inf(p.cost + 8.375 * p.x[1])
    return p


def test_supplier_switch_and_cost_recovery():
    p = suppliers()
    solution = p.solve()
    np.testing.assert_allclose(solution.program.H, [[1], [0]])
    assert len(solution.critical_regions) == 2
    for price, cost in [(7.86, 15.72), (8.375, 16.75), (8.89, 16.75)]:
        values = p.eval(price)
        used = values[p.x[0]]
        assert used + values[p.x[1]] == pytest.approx(2)
        assert values[p.cost[0]] == pytest.approx(price * used)
        assert solution.evaluate_objective(
            np.array([[price]])
        ) == pytest.approx(cost)
        if price != 8.375:
            assert used == pytest.approx(2 if price < 8.375 else 0)
    assert p.cost[0].eval(7.86) == pytest.approx(15.72)


def test_price_objective_replacement_preserves_solve_history():
    p = suppliers()
    p.solve()
    p.obj_max = sup(p.cost)
    second = p.solve()
    assert second.evaluate_objective(np.array([[8.89]])) == pytest.approx(
        -17.78
    )
    assert p.eval(8.89, n_sol=0)[p.cost[0]] == pytest.approx(0)
    assert p.eval(8.89, n_sol=1)[p.cost[0]] == pytest.approx(17.78)


@pytest.mark.parametrize("shared", [True, False])
def test_indexed_prices_and_aggregate_in_declaration_order(shared):
    p = Prg()
    p.i = I(size=2)
    p.x, p.cost, p.total = V(p.i), V(p.i), V()
    p.prices = T(_=(1, 4)) if shared else T(p.i, _=[(1, 4), (2, 5)])
    p.add_price(p.cost, p.x, p.prices, multiplier=2)
    p.quantity = p.x == [2, 3]
    p.aggregate = p.total == sigma(p.cost)
    p.obj_min = inf(p.total)
    sol = p.solve()
    point = (3,) if shared else (3, 4)
    values = p.eval(*point)
    expected = [12, 18 if shared else 24]
    assert [values[c] for c in p.cost] == pytest.approx(expected)
    assert values[p.total[0]] == pytest.approx(sum(expected))
    assert sol.evaluate_objective(np.array(point)[:, None]) == pytest.approx(
        sum(expected)
    )


def test_uncertain_demand_times_uncertain_price():
    p = Prg()
    p.x, p.cost = V(), V()
    p.price, p.demand = T(_=(2, 3)), T(_=(1, 2))
    p.bound = p.x >= p.demand
    p.add_price(p.cost, p.x, p.price)
    p.obj_min = inf(p.cost)
    sol = p.solve()
    assert p.eval(2.5, 1.5)[p.cost[0]] == pytest.approx(3.75)
    assert sol.evaluate_objective(np.array([[2.5], [1.5]])) == pytest.approx(
        3.75
    )


def test_price_in_budget_and_deterministic_export(tmp_path):
    p = suppliers()
    p.budget = p.cost <= 16
    with pytest.raises(ValueError, match="constraint matrix"):
        p.ppopt()
    with pytest.raises(ValueError, match="uncertain unit prices"):
        p.mps(str(tmp_path / "priced"))
    with pytest.raises(ValueError, match="uncertain unit prices"):
        p.gurobi()


def test_check_price_registration_before_mutation():
    p = suppliers()
    initial = p.unit_prices.copy()
    other = Prg()
    other.t = T(_=(1, 2))
    with pytest.raises(ValueError, match="another program"):
        p.add_price(p.cost, p.x[0], other.t)
    with pytest.raises(ValueError, match="dimensions"):
        p.add_price(p.cost, p.x, p.price)
    with pytest.raises(ValueError, match="different unit price"):
        p.add_price(p.cost, p.x[1], p.price)
    assert p.unit_prices == initial
