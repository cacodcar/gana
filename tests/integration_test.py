"""Integration tests"""

import pytest

from sympy import FiniteSet
from pyomo.environ import ConcreteModel, Set

from .element_test import p


@pytest.fixture
def m(p):
    """model"""
    cm = ConcreteModel()
    cm.i0 = p.i0.pyomo()
    return cm


def test_sympy(p):
    assert p.i0.sympy() == FiniteSet(0)


def test_pyomo(p, m):
    assert m.i0.at(1) == p.i0._[0]


def test_mps(p):
    assert p.i1.mps(0) == '_A'


def test_lp(p):
    assert p.i1.lp(0) == '_a'
