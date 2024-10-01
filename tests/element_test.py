import pytest

from gana.element.collection import S
from gana.element.parameter import P
from gana.element.variable import V
from gana.block.program import Prg


@pytest.fixture
def prg():
    """program"""
    return Prg()


@pytest.fixture
def s0():
    """|s0| = 1"""
    return S(0)


@pytest.fixture
def s1():
    """|s1| = 3"""
    return S('a', 'b', 'c')


@pytest.fixture
def s2():
    """|s2| = 4"""
    return S('a', 'd', 'e', 'f')


def test_set(s1, s2):

    assert (s1 & s2) == S('a')
    assert (s1 | s2) == S('a', 'b', 'c', 'd', 'e', 'f')
    assert (s1 ^ s2) == S('b', 'c', 'd', 'e', 'f')
    assert (s1 - s2) == S('b', 'c')


@pytest.fixture
def prgp0(prg):
    """no index + scalar parameter"""
    prg.p0 = P(_=5)
    return prg.p0


@pytest.fixture
def prgp1(prg):
    """no index + vector parameter"""
    prg.p1 = P(_=[4, 5, 6])
    return prg.p1


@pytest.fixture
def _prgp1(prgp1):
    """- prgp1"""
    return -prgp1


@pytest.fixture
def prgp2(prg, s1):
    """index + scalar parameter"""
    prg.p2 = P(s1, _=5)
    return prg.p2


@pytest.fixture
def _prgp2(prgp2):
    """- prgp2"""
    return -prgp2


@pytest.fixture
def prgp3(prg, s0, s1):
    """index + vector parameter"""
    prg.p3 = P(s0, s1, _=[4, 5, 6])
    return prg.p3


def test_prgparams(s0, s1, prgp0, prgp1, _prgp1, prgp2, _prgp2, prgp3):
    assert prgp0._ == 5
    assert -prgp0 == P(_=-5)
    assert prgp0.index == ()
    assert prgp1._ == [4, 5, 6]
    assert _prgp1._ == [-4, -5, -6]
    assert prgp2._ == [
        P('a', name='prgp2', _=5),
        P('b', name='prgp2', _=5),
        P('c', name='prgp2', _=5),
    ]
    assert _prgp2._ == [
        P('a', name='prgp2', _=-5),
        P('b', name='prgp2', _=-5),
        P('c', name='prgp2', _=-5),
    ]

    assert prgp2.index[0] == s1
    assert prgp3._ == [
        P(name='prgp3', _=[4]),
        P(name='prgp3', _=[5]),
        P(name='prgp3', _=[6]),
    ]
    assert prgp3._ == [P(s0, _=4), P(s0, _=[5]), P(s0, _=[6])]
    assert prgp3.idx() == [(0, 'a'), (0, 'b'), (0, 'c')]
    assert prgp3._[0].index == (0, 'a')
    assert prgp3._[1].index == (0, 'b')
    assert prgp3._[2].index == (0, 'c')


@pytest.fixture
def prgv1(prg, s1):
    """indexed variable"""
    prg.v1 = V(s1)
    return prg.v1


@pytest.fixture
def prgv2(prg, s0, s1):
    """multi-indexed variable"""
    prg.v2 = V(s0, s1)
    return prg.v2


def test_vars(prgv1, prgv2):

    assert prgv1._ == [V('a'), V('b'), V('c')]
    assert prgv2._ == [V(0, 'a'), V(0, 'b'), V(0, 'c')]
