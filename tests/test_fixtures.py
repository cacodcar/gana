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
    prg.i5 = prg.i0 * prg.i1
    prg.v0 = V()
    prg.v1 = V(prg.i1)
    prg.v1_ = V(prg.i1, nn=False)
    prg.v2 = V(prg.i0, prg.i1, itg=True)
    prg.v2_ = V(prg.i0, prg.i1, nn=False)
    prg.v3 = V(prg.i0, bnr=True)
    return prg


@pytest.fixture
def ps():
    """program"""
    prg = Prg()
    prg.i0 = I('0')
    prg.v0 = V()
    return prg


@pytest.fixture
def m(p):
    """model"""
    cm = ConcreteModel()
    cm.i0 = p.i0.pyomo()
    cm.v2 = p.v2.pyomo()
    cm.v3 = p.v3.pyomo()
    return cm
