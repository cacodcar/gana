import pytest
from src.gana.block.program import Prg
from src.gana.operators.composition import inf, sup
from src.gana.sets.index import I
from src.gana.sets.parameter import P
from src.gana.sets.variable import V
from src.gana.operators.sigma import sigma


@pytest.fixture
def psmall():
    p_ = Prg()
    p_.i = I(size=2)
    p_.ri = I('r')
    p_.x = V(p_.i)
    p_.y = V(p_.ri)
    p_.c1 = p_.x(p_.i[0]) + p_.x(p_.i[1]) <= 12
    p_.c2 = 2 * p_.x(p_.i[0]) + p_.x(p_.i[1]) <= 16
    p_.c3 = 4 * p_.y(p_.r) == 40
    p_.o = sup(40 * p_.x(p_.i[0]) + 30 * p_.x(p_.i[1]) - p_.y(p_.r))
    p_.opt()
    return p_


def test_solsmall(psmall):
    assert psmall.variables == [psmall.x[0], psmall.x[1], psmall.y[0]]
    assert psmall.obj() == -390.0
    assert psmall.A == [
        [1.0, 1.0, 0],
        [2.0, 1.0, 0],
        [0, 0, 4.0],
    ]
    assert psmall.A_with_NN == [
        [1.0, 1.0, 0],
        [2.0, 1.0, 0],
        [0, 0, 4.0],
        [-1.0, 0, 0],
        [0, -1.0, 0],
        [0, 0, -1.0],
    ]
    assert psmall.G == [[1.0, 1.0, 0], [2.0, 1.0, 0]]
    assert psmall.B == [12.0, 16.0, 40.0]
    assert psmall.B_with_NN == [12.0, 16.0, 40.0, 0, 0, 0]
    assert psmall.H == [[0, 0, 4.0]]
    # assert psmall._A == [
    #     [-1.0, 0, 0],
    #     [0, -1.0, 0],
    #     [0, 0, -1.0],
    #     [1.0, 1.0, 0],
    #     [2.0, 1.0, 0],
    #     [0, 0, 4.0],
    # ]
    assert psmall.NN == [[-1.0, 0, 0], [0, -1.0, 0], [0, 0, -1.0]]
    assert psmall.C == [-40.0, -30.0, 1.0]


@pytest.fixture
def p_energy():
    p = Prg()
    p.y = I(size=1)
    p.q = I(size=3)
    p.res_cons = I('solar')
    p.res_dem = I('power')
    p.res_stg = I('charge')
    p.res = p.res_cons | p.res_dem | p.res_stg
    p.pro_var = I('pv')
    p.pro_cer = I('li', 'li_d')
    p.pro = p.pro_var | p.pro_cer
    p.dm_fac = P(p.power, p.q, _=[0.5, 1, 0.5])
    p.pv_fac = P(p.pv, p.q, _=[1, 0, 0.5])
    p.demand = P(p.res_dem, p.q, _=[100] * 3)
    p.capex = P(p.pro, p.y, _=[5000, 1000, 0])
    p.fopex = P(p.pro, p.y, _=[500, 100, 0])
    p.vopex = P(p.pro, p.y, _=[10, 50, 0])
    p.capp = V(p.pro, p.y)
    p.caps = V(p.res_stg, p.y)
    p.sell = V(p.res_dem, p.q)
    p.con = V(p.res_cons, p.q)
    p.inv = V(p.res_stg, p.q)
    p.prod = V(p.pro, p.q)
    p.ex_cap = V(p.pro, p.y)
    p.ex_fop = V(p.pro, p.y)
    p.ex_vop = V(p.pro, p.y)

    p.con_vopex = p.ex_vop(p.pro, p.y) == p.vopex(p.pro, p.y) * sigma(
        p.prod(p.pro, p.q), p.q
    )
    p.con_capmax = p.capp(p.pro, p.y) <= 200
    p.con_capstg = p.caps(p.charge, p.y) <= 200
    p.con_consmax = p.con(p.res_cons, p.q) <= 200
    p.con_sell = p.sell(p.power, p.q) >= p.dm_fac(p.power, p.q) * p.demand(p.power, p.q)
    p.con_pv = p.prod(p.pv, p.q) <= p.pv_fac(p.pv, p.q) * p.capp(p.pv, p.y)
    p.con_prod = p.prod(p.pro_cer, p.q) <= p.capp(p.pro_cer, p.y)
    p.con_inv = p.inv(p.charge, p.q) <= p.caps(p.charge, p.y)
    p.con_capex = p.ex_cap(p.pro, p.y) == p.capex(p.pro, p.y) * p.capp(p.pro, p.y)
    p.con_fopex = p.ex_fop(p.pro, p.y) == p.fopex(p.pro, p.y) * p.capp(p.pro, p.y)
    p.con_solar = p.prod(p.pv, p.q) == p.con(p.solar, p.q)
    p.con_power = (
        p.prod(p.pv, p.q)
        - p.prod(p.li, p.q)
        + p.prod(p.li_d, p.q)
        - p.sell(p.power, p.q)
        == 0
    )
    p.con_charge = (
        p.prod(p.li, p.q)
        - p.prod(p.li_d, p.q)
        + p.inv(p.charge, p.q - 1)
        - p.inv(p.charge, p.q)
        == 0
    )
    p.o = inf(sigma(p.ex_cap) + sigma(p.ex_vop) + sigma(p.ex_fop))
    p.opt()
    return p


def test_sol(p_energy):
    assert p_energy.capp.sol(aslist=True) == [150.0, 100.0, 200.0]
    assert p_energy.caps.sol(aslist=True) == [200.0]
    assert p_energy.sell.sol(aslist=True) == [50.0, 100.0, 50.0]
    assert p_energy.con.sol(aslist=True) == [150.0, 0.0, 50.0]
    assert p_energy.inv.sol(aslist=True) == [100.0, 0.0, 0.0]
    assert p_energy.prod.sol(aslist=True) == [
        150.0,
        0.0,
        50.0,
        100.0,
        0.0,
        0.0,
        0.0,
        100.0,
        0.0,
    ]
    assert p_energy.ex_cap.sol(aslist=True) == [750000.0, 100000.0, 0.0]
    assert p_energy.ex_fop.sol(aslist=True) == [75000.0, 10000.0, 0.0]
    assert p_energy.ex_vop.sol(aslist=True) == [2000.0, 5000.0, 0.0]
    assert p_energy.o.sol(True) == 942000.0


@pytest.fixture
def p1():
    p1_ = Prg()
    p1_.i = I(size=2)
    p1_.j = I('a', 'b', 'c')
    p1_.x = V(p1_.i)
    p1_.y = V(p1_.j)
    p1_.c1 = sum(p1_.x) <= 12
    p1_.c2 = p1_.y(p1_.j) <= 20
    p1_.o1 = sup(40 * sum(p1_.x) + 30 * sum(p1_.y))
    return p1_


@pytest.fixture
def p2():
    p2_ = Prg()
    p2_.k = I(size=2)
    p2_.z = V(p2_.k)
    p2_.c3 = sum(p2_.z) >= 4
    p2_.o2 = inf(3 * sum(p2_.z))
    return p2_


# def test_padd(p1, p2):
#     p = p1 + p2
#     # TODO: Fix this test
#     assert p.A == [
#         [-1.0, 0, 0, 0, 0, 0, 0],
#         [0, -1.0, 0, 0, 0, 0, 0],
#         [0, 0, -1.0, 0, 0, 0, 0],
#         [0, 0, 0, -1.0, 0, 0, 0],
#         [0, 0, 0, 0, -1.0, 0, 0],
#         [0, 0, 0, 0, 0, -1.0, 0],
#         [0, 0, 0, 0, 0, 0, -1.0],
#         [1.0, 1.0, 0, 0, 0, 0, 0],
#         [0, 0, 1.0, 0, 0, 0, 0],
#         [0, 0, 0, 1.0, 0, 0, 0],
#         [0, 0, 0, 0, 1.0, 0, 0],
#         [0, 0, 0, 0, 0, -1.0, -1.0],
#     ]
#     assert p.C == [[-40.0, -40.0, -30.0, -30.0, -30.0, 0, 0], [0, 0, 0, 0, 0, 3.0, 3.0]]
#     assert p.variables == [p.x[0], p.x[1], p.y[0], p.y[1], p.y[2], p.z[0], p.z[1]]
#     assert p.objectives == [p.o1, p.o2]
