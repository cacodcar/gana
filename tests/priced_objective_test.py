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


def test_price_equation_in_latex_and_notebook(monkeypatch):
    p = Prg()
    p.x, p.cost, p.t = V(), V(), T(_=(1, 3))
    p.add_price(p.cost, p.x, p.t, multiplier=2)
    equation = (
        rf"{p.cost[0].latex()} = 2 \cdot {p.t[0].latex()} "
        rf"\cdot {p.x[0].latex()}"
    )
    assert equation in p.latex(category="Calculations")
    assert equation not in p.latex(category="Capacity")
    displayed = []
    monkeypatch.setattr("src.gana.block.program.display", displayed.append)
    p.show()
    assert equation in [item.data for item in displayed]


def test_price_registration_rejects_invalid_inputs_atomically():
    p = suppliers()
    initial = p.unit_prices.copy()
    with pytest.raises(TypeError, match="two variables and a theta"):
        p.add_price(p.cost, p.x[0], 8.375)
    with pytest.raises(ValueError, match="Register the account"):
        p.add_price(V(), p.x[0], p.price)
    with pytest.raises(ValueError, match="finite"):
        p.add_price(p.cost, p.x[0], p.price, multiplier=float("nan"))
    assert p.unit_prices == initial


def test_priced_model_requires_an_objective_and_continuous_decisions():
    p = Prg()
    p.units, p.spend, p.price = V(itg=True), V(), T(_=(1, 3))
    p.add_price(p.spend, p.units, p.price)
    with pytest.raises(ValueError, match="Set an objective"):
        p.ppopt()
    p.obj = inf(p.spend)
    with pytest.raises(ValueError, match="continuous decisions"):
        p.ppopt()


def test_chaining_two_uncertain_prices_is_rejected():
    p = suppliers()
    p.tax, p.rate = V(), T(_=(0.05, 0.1))
    p.add_price(p.tax, p.cost, p.rate)
    with pytest.raises(ValueError, match="cannot depend on another price"):
        p.ppopt()


def test_negative_price_requires_an_account_that_allows_credits():
    p = Prg()
    p.units, p.net, p.price = V(), V(nn=False), T(_=(-2, 2))
    p.add_price(p.net, p.units, p.price)
    p.demand = p.units == 3
    p.obj = inf(p.net)
    p.solve()
    assert p.eval(-2)[p.net[0]] == pytest.approx(-6)
    assert p.eval(2)[p.net[0]] == pytest.approx(6)
    p.nonnegative_spend = V()
    p.add_price(p.nonnegative_spend, p.units, p.price)
    with pytest.raises(ValueError, match="Nonnegativity of a priced account"):
        p.ppopt()


def test_equal_charge_and_refund_restrict_the_parameter_domain():
    p = Prg()
    p.units, p.charge, p.refund, p.net = V(), V(), V(nn=False), V()
    p.price, p.minimum = T(_=(2, 4)), T(_=(-1, 1))
    p.add_price(p.charge, p.units, p.price)
    p.add_price(p.refund, p.units, p.price, multiplier=-1)
    p.total = p.net == p.charge + p.refund
    p.required_units = p.units == 2
    p.minimum_net = p.net >= p.minimum
    p.obj = inf(p.charge)
    p.solve()
    values = p.eval(3, -1)
    assert [values[v[0]] for v in (p.charge, p.refund, p.net)] == [6, -6, 0]
    assert p.eval(3, 0)[p.net[0]] == 0
    with pytest.raises(TypeError, match="No solution"):
        p.eval(3, 1)
    p.impossible = p.net == 1
    with pytest.raises(ValueError, match="Infeasible constant constraint"):
        p.ppopt()
