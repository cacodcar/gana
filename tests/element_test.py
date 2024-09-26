import pytest

from src.gana.element.s import S
from src.gana.element.p import P
from src.gana.element.v import V
from src.gana.block.prg import Prg


@pytest.fixture
def prg():
    """program"""
    return Prg()


@pytest.fixture
def s1():
    return S('a', 'b', 'c')


@pytest.fixture
def s2():
    return S('a', 'd', 'e', 'f')


def test_set(s1, s2):

    assert (s1 & s2) == S('a')
    assert (s1 | s2) == S('a', 'b', 'c', 'd', 'e', 'f')
    assert (s1 ^ s2) == S('b', 'c', 'd', 'e', 'f')
    assert (s1 - s2) == S('b', 'c')


@pytest.fixture
def p0():
    """no index + scalar parameter"""
    return P(_=5)


@pytest.fixture
def p1():
    """no index + vector parameter"""
    return P(_=[4, 5, 6])


@pytest.fixture
def p2(s1):
    """index + scalar parameter"""
    return P(s1, _=5)


@pytest.fixture
def p3(s2):
    """index + vector parameter"""
    return P(s2, _=[4, 5, 6, 7])


@pytest.fixture
def p4(s1, s2):
    """indices + vector parameter"""
    return P(s1, s2, _=list(range(12)))


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
def prgp2(prg, s1):
    """index + scalar parameter"""
    prg.p2 = P(s1, _=5)
    return prg.p2


@pytest.fixture
def prgp3(prg, s2):
    """index + vector parameter"""
    prg.p3 = P(s2, _=[4, 5, 6, 7])
    return prg.p3


@pytest.fixture
def prgp4(prg, s1, s2):
    """indices + vector parameter"""
    prg.p4 = P(s1, s2, _=list(range(12)))
    return prg.p4


def test_params(p0, p1, p2, p3, p4):

    assert p0._ == 5
    assert p1._ == [4, 5, 6]
    assert p2._ == [5, 5, 5]
    assert p3._ == [4, 5, 6, 7]
    assert p4._ == list(range(12))


def test_prgparams(prgp0, prgp1, prgp2, s1, s2, prgp4):

    assert prgp0._ == 5
    assert prgp1._ == [P(_=4), P(_=5), P(_=6)]
    assert prgp2._ == [P('a', _=5), P('b', _=5), P('c', _=5)]


# @pytest.fixture
# def v():
#     """empty variable"""
#     return V()


# @pytest.fixture
# def v1(s1):
#     """variable"""
#     return V(s1)


# @pytest.fixture
# def v2(s2):
#     """variable"""
#     return V(s2)
