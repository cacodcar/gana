import pytest

from src.gana.sets.index import I
from src.gana.sets.parameter import P
from src.gana.sets.variable import V
from src.gana.block.program import Prg
from pyomo.environ import ConcreteModel, Set


@pytest.fixture
def p():
    """program"""
    prg = Prg()
    prg.i0 = I('0')
    prg.i1 = I('a', 'b', 'c')
    prg.i2 = I('d', 'e')
    prg.i3 = I('a', 'b', 'c', 'd', 'e')
    prg.i4 = I('a', 'b', 'c')
    prg.v0 = V(prg.i0)
    prg.v1 = V(prg.i1)
    prg.v1_ = V(prg.i1, nn=False)
    prg.v2 = V(prg.i0, prg.i1, itg=True)
    prg.v2_ = V(prg.i0, prg.i1, nn=False)
    prg.v3 = V(prg.i0, bnr=True)
    prg.p0 = P(prg.i0, prg.i1, _=[1, 2, 5])
    prg.p1 = P(prg.i0, _=[4])
    prg.p2 = P(prg.i0, prg.i1, _=[6, 8, 3])
    prg.p3 = P(prg.i0, _=[True])
    prg.p4 = P(prg.i0, prg.i1, _=[10, 10, 10])
    prg.p5 = P(prg.i0, prg.i1, _=[4, 2, 7])
    prg.f1 = prg.v2_ + prg.v2
    prg.f2 = prg.v2_ - prg.v2
    prg.f3 = prg.v2_ * prg.v2
    prg.f4 = prg.v2_ / prg.v2
    prg.c1 = prg.v2_ == prg.v2
    prg.c2 = prg.v2_ >= prg.v2
    prg.c3 = prg.v2_ <= prg.v2
    prg.c4 = prg.v2_ > prg.v2
    prg.c5 = prg.v2_ < prg.v2
    return prg


@pytest.fixture
def ps():
    """program"""
    prg = Prg()
    prg.i0 = I('0')
    prg.v0 = V(prg.i0)
    prg.p1 = P(prg.i0, _=[4])
    return prg


@pytest.fixture
def m(p):
    """model"""
    cm = ConcreteModel()
    cm.i0 = p.i0.pyomo()
    cm.v2 = p.v2.pyomo()
    cm.v3 = p.v3.pyomo()
    return cm
