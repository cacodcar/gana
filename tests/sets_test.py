"""Element Tests"""

import pytest

from IPython.display import Math

from src.gana.sets.index import I

from src.gana.sets.parameter import P
from src.gana.sets.variable import V
from src.gana.sets.function import F
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
    # assert p.v2[(0, 'a')] == p.v2._[0]
    # assert p.v1[0] == p.v1._[0]


# @pytest.fixture
# def prgp0(prg):
#     """no index + scalar parameter"""
#     prg.p0 = P(_=5)
#     return prg.p0


# @pytest.fixture
# def prgp1(prg):
#     """no index + vector parameter"""
#     prg.p1 = P(_=[4, 5, 6])
#     return prg.p1


# @pytest.fixture
# def _prgp1(prgp1):
#     """- prgp1"""
#     return -prgp1


# @pytest.fixture
# def prgp2(prg, s1):
#     """index + scalar parameter"""
#     prg.p2 = P(s1, _=5)
#     return prg.p2


# @pytest.fixture
# def _prgp2(prgp2):
#     """- prgp2"""
#     return -prgp2


# @pytest.fixture
# def prgp3(prg, s0, s1):
#     """index + vector parameter"""
#     prg.p3 = P(s0, s1, _=[4, 5, 6])
#     return prg.p3


# def test_prgparams(s0, s1, prgp0, prgp1, _prgp1, prgp2, _prgp2, prgp3):
#     assert prgp0._ == 5
#     assert -prgp0 == P(_=-5)
#     assert prgp0.index == ()
#     assert prgp1._ == [4, 5, 6]
#     assert _prgp1._ == [-4, -5, -6]
#     assert prgp2._ == [
#         P('a', name='prgp2', _=5),
#         P('b', name='prgp2', _=5),
#         P('c', name='prgp2', _=5),
#     ]
#     assert _prgp2._ == [
#         P('a', name='prgp2', _=-5),
#         P('b', name='prgp2', _=-5),
#         P('c', name='prgp2', _=-5),
#     ]

#     assert prgp2.index[0] == s1
#     assert prgp3._ == [
#         P(name='prgp3', _=[4]),
#         P(name='prgp3', _=[5]),
#         P(name='prgp3', _=[6]),
#     ]
#     assert prgp3._ == [P(s0, _=4), P(s0, _=[5]), P(s0, _=[6])]
#     assert prgp3.idx() == [(0, 'a'), (0, 'b'), (0, 'c')]
#     assert prgp3._[0].index == (0, 'a')
#     assert prgp3._[1].index == (0, 'b')
#     assert prgp3._[2].index == (0, 'c')


# @pytest.fixture
# def prgv1(prg, s1):
#     """indexed variable"""
#     prg.v1 = V(s1)
#     return prg.v1


# @pytest.fixture
# def prgv2(prg, s0, s1):
#     """multi-indexed variable"""
#     prg.v2 = V(s0, s1)
#     return prg.v2


# def test_vars(prgv1, prgv2):

#     assert prgv1._ == [V('a'), V('b'), V('c')]
#     assert prgv2._ == [V(0, 'a'), V(0, 'b'), V(0, 'c')]
