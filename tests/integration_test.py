"""Integration tests"""

import pytest

from sympy import FiniteSet, symbols, IndexedBase, Idx

from .test_fixtures import p, m


def test_call(p):
    assert p.i0()
    assert p.v1()


def test_latex(p):
    assert p.i0.latex() == '\\mathcal{i0}'
    assert p.i0.latex(True) == '\\mathcal{i0}\\in\\{0\\}'
    assert p.v1.latex() == r'v1_{i1}'
    assert p.p1.latex() == r'P1_{i0}'


def test_sympy(p):
    assert p.i0.sympy() == FiniteSet(0)
    assert p.v1.sympy() == IndexedBase('v1')[symbols('i1', cls=Idx)]
    assert p.p1.sympy() == IndexedBase('P1')[symbols('i0', cls=Idx)]


def test_pyomo(p, m):
    assert m.i0.at(1) == p.i0._[0]
    assert list(m.v2.extract_values().keys()) == [
        (p.i0._[0], p.i1._[0]),
        (p.i0._[0], p.i1._[1]),
        (p.i0._[0], p.i1._[2]),
    ]


def test_mps(p):
    assert p.i1.mps(0) == '_A'
    assert p.v3.mps() == 'V3'


def test_lp(p):
    assert p.i1.lp(0) == '_a'
    assert p.v3.lp() == 'v3'
