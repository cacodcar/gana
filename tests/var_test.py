from operator import is_

import pytest
from src.gana.block.program import Prg
from src.gana.sets.index import I
from src.gana.sets.variable import V


@pytest.fixture()
def p():
    p_ = Prg()
    p_.y = I(size=2)
    p_.q = I(size=4)
    p_.p = I('pv', 'wf')
    p_.cap = V(p_.p, p_.y)
    p_.prod = V(p_.p, p_.y, p_.q)
    p_.x = V(p_.p, p_.y, bnr=True)
    p_.n = V(p_.p, p_.y, itg=True)
    p_.rev = V(p_.p, p_.y, p_.q, nn=False)
    return p_


def test_var(p):
    assert is_(p.cap(p.pv, p.y[0])[0], p.cap[0])
    assert is_(p.cap(p.pv, p.y[1])[0], p.cap[1])
    assert is_(p.cap(p.wf, p.y[0])[0], p.cap[2])
    assert is_(p.cap(p.wf, p.y[1])[0], p.cap[3])
    assert p.cap(p.pv, p.y)._ == [p.cap[i] for i in range(2)]
    assert p.x.itg
    assert not p.n.bnr
    assert p.cap.nn
    assert len(p.prod) == 16
    assert p.sets.variable == [p.cap, p.prod, p.x, p.n, p.rev]
    assert p.variables == p.cap._ + p.prod._ + p.x._ + p.n._ + p.rev._
    assert is_(p.variables[0].parent, p.cap)
    assert p.variables[0].pos == 0
    assert p.variables[-17].itg
    assert p.variables[-21].bnr
    assert not p.variables[-1].nn
