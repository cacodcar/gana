import pytest
from src.gana.block.program import Prg
from src.gana.operations.composition import inf, sup
from src.gana.sets.index import I
from src.gana.sets.parameter import P
from src.gana.sets.variable import V


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
    assert psmall.vars() == {psmall.x[0]: 4.0, psmall.x[1]: 8.0, psmall.y[0]: 10.0}
    assert psmall.obj() == -390.0
    assert psmall.A == [
        [-1.0, 0, 0],
        [0, -1.0, 0],
        [0, 0, -1.0],
        [1.0, 1.0, 0],
        [2.0, 1.0, 0],
        [0, 0, 4.0],
    ]
    assert psmall.G == [[1.0, 1.0, 0], [2.0, 1.0, 0]]
    assert psmall.B == [0, 0, 0, 12.0, 16.0, 40.0]
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
def p():
    p_ = Prg()
    p_.y = I(size=1)
    p_.q = I(size=3)
    p_.res_cons = I('solar')
    p_.res_dem = I('power')
    p_.res_stg = I('charge')
    p_.res = p_.res_cons | p_.res_dem | p_.res_stg
    p_.pro_var = I('pv')
    p_.pro_cer = I('li', 'li_d')
    p_.pro = p_.pro_var | p_.pro_cer
    p_.dm_fac = P(p_.power, p_.q, _=[0.5, 1, 0.5])
    p_.pv_fac = P(p_.pv, p_.q, _=[1, 0, 0.5])
    p_.demand = P(p_.res_dem, p_.q, _=[100] * 3)
    p_.capex = P(p_.pro, p_.y, _=[5000, 1000, 0])
    p_.fopex = P(p_.pro, p_.y, _=[500, 100, 0])
    p_.vopex = P(p_.pro, p_.y, _=[10, 50, 0])
    p_.cap_p = V(p_.pro, p_.y)
    p_.cap_s = V(p_.res_stg, p_.y)
    p_.sell = V(p_.res_dem, p_.q)
    p_.con = V(p_.res_cons, p_.q)
    p_.inv = V(p_.res_stg, p_.q)
    p_.prod = V(p_.pro, p_.q)
    p_.ex_cap = V(p_.pro, p_.y)
    p_.ex_fop = V(p_.pro, p_.y)
    p_.ex_vop = V(p_.pro, p_.y)
    p_.con_vopex = p_.ex_vop(p_.pro, p_.y) == p_.vopex(p_.pro, p_.y) * sum(
        p_.prod(p_.pro, q) for q in p_.q
    )
    p_.con_capmax = p_.cap_p(p_.pro, p_.y) <= 200
    p_.con_capstg = p_.cap_s(p_.charge, p_.y) <= 200
    p_.con_consmax = p_.con(p_.res_cons, p_.q) <= 200
    p_.con_sell = p_.sell(p_.power, p_.q) >= p_.dm_fac(p_.power, p_.q) * p_.demand(
        p_.power, p_.q
    )
    p_.con_pv = p_.prod(p_.pv, p_.q) <= p_.pv_fac(p_.pv, p_.q) * p_.cap_p(p_.pv, p_.y)
    p_.con_prod = p_.prod(p_.pro_cer, p_.q) <= p_.cap_p(p_.pro_cer, p_.y)
    p_.con_inv = p_.inv(p_.charge, p_.q) <= p_.cap_s(p_.charge, p_.y)
    p_.con_capex = p_.ex_cap(p_.pro, p_.y) == p_.capex(p_.pro, p_.y) * p_.cap_p(
        p_.pro, p_.y
    )
    p_.con_fopex = p_.ex_fop(p_.pro, p_.y) == p_.fopex(p_.pro, p_.y) * p_.cap_p(
        p_.pro, p_.y
    )
    p_.con_solar = p_.prod(p_.pv, p_.q) == p_.con(p_.solar, p_.q)
    p_.con_power = (
        sum(p_.prod(i, p_.q) for i in p_.pro_var)
        - p_.prod(p_.li, p_.q)
        + p_.prod(p_.li_d, p_.q)
        - p_.sell(p_.power, p_.q)
        == 0
    )
    p_.con_charge = (
        p_.prod(p_.li, p_.q)
        - p_.prod(p_.li_d, p_.q)
        + p_.inv(p_.charge, p_.q - 1)
        - p_.inv(p_.charge, p_.q)
        == 0
    )
    p_.o = inf(sum(p_.ex_cap) + sum(p_.ex_vop) + sum(p_.ex_fop))
    p_.opt()
    return p_


def test_sol(p):
    assert p.cap_p.sol(True) == [150.0, 100.0, 200.0]
    assert p.cap_s.sol(True) == [200.0]
    assert p.sell.sol(True) == [50.0, 100.0, 50.0]
    assert p.con.sol(True) == [150.0, 0.0, 50.0]
    assert p.inv.sol(True) == [100.0, 0.0, 0.0]
    assert p.prod.sol(True) == [150.0, 0.0, 50.0, 100.0, 0.0, 0.0, 0.0, 100.0, 0.0]
    assert p.ex_cap.sol(True) == [750000.0, 100000.0, 0.0]
    assert p.ex_fop.sol(True) == [75000.0, 10000.0, 0.0]
    assert p.ex_vop.sol(True) == [2000.0, 5000.0, 0.0]
    assert p.o.sol(True) == 942000.0


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
