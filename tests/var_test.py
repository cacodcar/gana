from operator import is_

import pytest
from src.gana.block.program import Prg
from src.gana.sets.index import I
from src.gana.sets.parameter import P
from src.gana.sets.variable import V


@pytest.fixture()
def p():
    _p = Prg()
    _p.y = I(size=2)
    _p.q = I(size=4)
    _p.v = V(tag='Empty Variable')
    _p.p = I('pv', 'wf')
    _p.cap = V(_p.p, _p.y, tag='Compound Index Variable')
    _p.prod = V(_p.p, _p.y, _p.q)
    _p.x = V(_p.p, _p.y, bnr=True, tag='Binary Variable')
    _p.n = V(_p.p, _p.y, itg=True, tag='Integer Variable')
    _p.rev = V(_p.p, _p.y, _p.q, nn=False, tag='Free Variable')
    _p.i = I(size=3)
    _p.p1 = P(_p.i, _=[1, 2, 4])
    _p.v1 = V(_p.i)
    _p.f1 = _p.v1 + 1
    _p.f2 = 1 + _p.v1
    _p.f3 = _p.v1 + [1, 2, 3]
    _p.f4 = [1, 2, 3] + _p.v1
    _p.f5 = _p.v1 + _p.p1
    _p.f6 = _p.p1 + _p.v1
    return _p


def test_var(p):
    assert p.v.args == {
        'itg': False,
        'nn': True,
        'bnr': False,
        'mutable': False,
        'tag': 'Empty Variable',
        'ltx': r'{v}',
    }
    assert is_(p.cap(p.pv, p.y[0])[0], p.cap[0])
    assert is_(p.cap(p.pv, p.y[1])[0], p.cap[1])
    assert is_(p.cap(p.wf, p.y[0])[0], p.cap[2])
    assert is_(p.cap(p.wf, p.y[1])[0], p.cap[3])
    assert p.cap(p.pv, p.y)._ == [p.cap[i] for i in range(2)]
    assert p.x.itg
    assert not p.n.bnr
    assert p.cap.nn
    assert len(p.prod) == 16
    assert p.variable_sets == [p.v, p.cap, p.prod, p.x, p.n, p.rev, p.v1]
    assert p.variable_sets[0].n == 0
    assert p.cap(p.pv, p.y)._ == [p.cap[0], p.cap[1]]
    assert p.prod(p.wf, p.y, p.q[1:3])._ == [
        p.prod[9],
        p.prod[10],
        p.prod[13],
        p.prod[14],
    ]


def test_add_var(p):
    assert p.f1.one.name == p.v1.name
    assert p.f1.two._ == [1, 1, 1]
    assert p.f2.one.name == p.v1.name
    assert p.f2.two._ == [1, 1, 1]
    assert p.f3.one.name == p.v1.name
    assert p.f3.two._ == [1, 2, 3]
    assert p.f4.one.name == p.v1.name
    assert p.f4.two._ == [1, 2, 3]
    assert p.f5.one.name == p.v1.name
    assert p.f5.two._ == [1, 2, 4]
    assert p.f6.one.name == p.v1.name
    assert p.f6.two._ == [1, 2, 4]
