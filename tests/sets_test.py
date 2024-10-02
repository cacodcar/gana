"""Element Tests"""

import pytest

from IPython.display import Math

from src.gana.sets.index import I

from src.gana.sets.parameter import P
from src.gana.sets.variable import V
from src.gana.sets.function import F
from src.gana.sets.constraint import C
from src.gana.block.program import Prg

from .test_fixtures import p, ps


def test_rep(p, ps):
    assert str(p.i0) == 'i0'
    assert repr(p.i0) == 'i0'
    assert hash(p.i0) == hash(ps.i0)
    assert str(p.v0) == 'v0'
    assert repr(p.v0) == 'v0'
    assert hash(p.v0) == hash(ps.v0)


def test_index(p):
    with pytest.raises(ValueError):
        I('a', 'a', 'b')
    assert (p.i1 & p.i3) == p.i4
    assert (p.i1 & p.i3) == (p.i3 & p.i1)
    assert (p.i1 | p.i2) == p.i3
    assert (p.i1 | p.i2) == (p.i2 | p.i1)
    assert (p.i1 ^ p.i2) == p.i3
    assert (p.i1 ^ p.i2) == (p.i2 ^ p.i1)
    assert (p.i3 - p.i1) == p.i2
    assert p.i5._ == [
        (p.i0._[0], p.i1._[0]),
        (p.i0._[0], p.i1._[1]),
        (p.i0._[0], p.i1._[2]),
    ]

    assert len(p.i1) == 3
    assert p.i1[0] == p.i1._[0]
    assert p.i1._[2] in p.i1
    assert p.i1 == p.i4
    assert list(p.i1) == p.i1._


def test_variable(p):
    with pytest.raises(ValueError):
        V(bnr=True, nn=False)
    assert p.v3.itg
    assert p.v3.nn

    assert p.v1()
    assert len(p.v1) == 3
    assert -p.v1 == F(rel='-', two=p.v1)
    assert +p.v1 == F(rel='+', two=p.v1)
    assert p.v2 + p.v2_ == F(one=p.v2, rel='+', two=p.v2_)
    assert p.v2 - p.v2_ == F(one=p.v2, rel='-', two=p.v2_)
    assert sum(p.v1) == p.v1['a'] + p.v1['b'] + p.v1['c']
    assert p.v1['a'] == p.v1[0]
    assert 0 + p.v1 == p.v1 + 0


def test_function(p):
    assert p.f1.one == p.v2_
    assert p.f1.rel == '+'
    assert p.f1.two == p.v2
    assert p.f2.one == p.v2_
    assert p.f2.rel == '-'
    assert p.f2.two == p.v2
    assert p.f3.one == p.v2_
    assert p.f3.rel == '×'
    assert p.f3.two == p.v2
    assert p.f4.one == p.v2_
    assert p.f4.rel == '÷'
    assert p.f4.two == p.v2


def test_constraint(p):
    assert p.c1.lhs == p.v2_
    assert p.c1.rel == 'eq'
    assert p.c1.rhs == p.v2
    assert p.c2.lhs == p.v2_
    assert p.c2.rel == 'ge'
    assert p.c2.rhs == p.v2
    assert p.c3.lhs == p.v2_
    assert p.c3.rel == 'le'
    assert p.c3.rhs == p.v2
    assert p.c4.lhs == p.v2_
    assert p.c4.rel == 'ge'
    assert p.c4.rhs == p.v2
    assert p.c5.lhs == p.v2_
    assert p.c5.rel == 'le'
    assert p.c5.rhs == p.v2
