"""Energy System Model Example."""

from gana import I, P, Prg, V, inf, sigma


def energy_system():
    """A small energy system model with solar power, storage, and demand management."""
    p = Prg()
    p.y = I(size=1)
    p.q = I(size=3)
    p.res_cons = I("solar")
    p.res_dem = I("power")
    p.res_stg = I("charge")
    p.res = p.res_cons | p.res_dem | p.res_stg
    p.pro_var = I("pv")
    p.pro_cer = I("li", "li_d")
    p.pro = p.pro_var | p.pro_cer
    p.dm_fac = P(p.power, p.q, _=[0.5, 1, 0.5])
    p.pv_fac = P(p.pv, p.q, _=[1, 0, 0.5])
    p.demand = P(p.res_dem, p.q, _=[100] * 3)
    p.capex = P(p.pro, p.y, _=[5000, 1000, 0])
    p.fopex = P(p.pro, p.y, _=[500, 100, 0])
    p.vopex = P(p.pro, p.y, _=[10, 50, 0])
    p.capp = V(p.pro, p.y, ltx=r"cap^{p}")
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
    return p


p = energy_system()
