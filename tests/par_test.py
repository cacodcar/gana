"""Parameter tests"""

import math
import pytest
from hypothesis import given
from hypothesis import strategies as st
from src.gana.block.program import Prg
from src.gana.sets.cases import PCase
from src.gana.sets.index import I
from src.gana.sets.parameter import P


@pytest.fixture()
def p():
    _p = Prg()
    _p.i = I(size=3)
    _p.p2 = P(_p.i, _=5)
    _p.p3 = P(_p.i, _=[1, 2, 3])
    _p.p4 = P(_p.i, _=[-3, 1, 0])
    _p.p5 = _p.p3 + _p.p4
    _p.p6 = _p.p3 - _p.p4
    _p.p7 = _p.p3 * _p.p4
    _p.p8 = _p.p4 / _p.p3
    _p.p9 = P(_p.i, _=10)
    _p.p10 = P(_p.i, _=-5)
    _p.p11 = _p.p2 + _p.p9
    _p.p12 = _p.p2 - _p.p9
    _p.p13 = _p.p2 * _p.p9
    _p.p14 = _p.p2 / _p.p9
    _p.p15 = _p.p2 + _p.p10
    _p.p16 = _p.p2 - _p.p10
    _p.p17 = _p.p2 * _p.p10
    _p.p18 = _p.p2 / _p.p10
    _p.p19 = -_p.p3
    return _p


def test_parameter(p):
    with pytest.raises(ValueError):
        p.p5 = P(p.i, _=[4, 5, 6, 7])
    assert p.p2._ == [5, 5, 5]
    assert p.p2.case == PCase.NUM
    assert p.p2.index == (p.i,)
    assert p.p5._ == [-2, 3, 3]
    assert p.p5.case == PCase.SET
    assert p.p6._ == [4, 1, 3]
    assert p.p6.case == PCase.SET
    assert p.p7._ == [-3, 2, 0]
    assert p.p7.case == PCase.SET
    assert p.p8._ == [-3, 0.5, 0.0]
    assert p.p8.case == PCase.SET
    assert p.p3._ == [1, 2, 3]
    assert p.p3.case == PCase.SET
    assert p.p11._ == [15] * 3
    assert p.p11.name == '15.0'
    assert p.p11.case == PCase.NUM
    assert p.p12._ == [-5] * 3
    assert p.p12.name == '-5.0'
    assert p.p12.case == PCase.NEGNUM
    assert p.p13._ == [50] * 3
    assert p.p13.name == '50.0'
    assert p.p13.case == PCase.NUM
    assert p.p14._ == [0.5] * 3
    assert p.p14.name == '0.5'
    assert p.p14.case == PCase.NUM
    assert p.p15 == 0
    assert p.p16._ == [10] * 3
    assert p.p16.name == '10.0'
    assert p.p16.case == PCase.NUM
    assert p.p17._ == [-25] * 3
    assert p.p17.name == '-25.0'
    assert p.p17.case == PCase.NEGNUM
    assert p.p18._ == [-1.0] * 3
    assert p.p18.name == '-1.0'
    assert p.p18.case == PCase.NEGNUM
    assert p.p19._ == [-1, -2, -3]
    assert p.p19.case == PCase.NEGSET


# this contains one list (a) that is just a general list of floats,
# one list (b) that is a list of floats with values >= 1,
# and one list (c) that is a list of floats with values >= 0 and <= 10.
same_size_lists = st.integers(min_value=1, max_value=100).flatmap(
    lambda x: st.tuples(
        st.lists(
            st.floats(max_value=10**9),
            min_size=x,
            max_size=x,
        ),
        st.lists(
            st.floats(min_value=1, max_value=10**9),
            min_size=x,
            max_size=x,
        ),
        st.lists(
            st.floats(min_value=0, max_value=10),
            min_size=x,
            max_size=x,
        ),
        st.just(x),  # also return x if you need it
    )
)


@given(same_size_lists)
def test_pset_operations(data):
    a, b, c, x = data
    p = Prg()
    p.i = I(size=x)
    p.a = P(p.i, _=a)
    p.b = P(p.i, _=b)
    p.c = P(p.i, _=c)

    # sanity check
    assert len(a) == len(b) == x
    p.add = p.a + p.b
    assert p.add._ == [a[i] + b[i] for i in range(x)]
    p.sub = p.a - p.b
    assert p.sub._ == [a[i] - b[i] for i in range(x)]
    p.mul = p.a * p.b
    assert p.mul._ == [a[i] * b[i] for i in range(x)]
    p.div = p.a / p.b
    assert p.div._ == [a[i] / b[i] for i in range(x)]
    p.mod = p.a % p.b

    if not any(math.isnan(x) for x in p.mod._):

        assert p.mod._ == [a[i] % b[i] for i in range(x)]

    p.pow = p.b**p.c
    assert p.pow._ == [b[i] ** c[i] for i in range(x)]
    p.neg = -p.a
    assert p.neg._ == [-a[i] for i in range(x)]
    p.abs = abs(p.a)
    assert p.abs._ == [abs(a[i]) for i in range(x)]
    p.floor = p.a // p.b
    if not any(math.isnan(x) for x in p.floor._):
        assert p.floor._ == [math.floor(a[i] // b[i]) for i in range(x)]


test_pset_operations()


@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(allow_nan=False, allow_infinity=False, min_value=1, max_value=10**9),
    st.integers(min_value=1, max_value=50),
)
def test_pnum_operations(a, b, x):
    p = Prg()
    p.i = I(size=x)
    p.a = P(p.i, _=a)
    p.b = P(p.i, _=b)

    # sanity check
    assert all(math.isclose(v, a, rel_tol=1e-9, abs_tol=0.0) for v in p.a._)
    assert all(math.isclose(v, b, rel_tol=1e-9, abs_tol=0.0) for v in p.b._)

    p.add = p.a + p.b
    if a == -b:
        assert p.add == 0
    else:
        assert all(math.isclose(v, a + b, rel_tol=1e-9, abs_tol=0.0) for v in p.add._)

    p.sub = p.a - p.b
    if a == b:
        assert p.sub == 0
    else:
        assert all(math.isclose(v, a - b, rel_tol=1e-9, abs_tol=0.0) for v in p.sub._)

    p.mul = p.a * p.b
    if not isinstance(p.mul, (int, float)):
        assert all(math.isclose(v, a * b, rel_tol=1e-9, abs_tol=0.0) for v in p.mul._)
    else:
        assert p.mul == 0

    p.div = p.a / p.b
    if a == b:
        assert p.div == 1
    else:
        if not isinstance(p.mul, (int, float)):
            assert all(
                math.isclose(v, a / b, rel_tol=1e-9, abs_tol=0.0) for v in p.div._
            )
        else:
            assert p.div == 0


test_pnum_operations()


@given(
    st.lists(
        st.floats(
            min_value=-(10**9), max_value=10**9, allow_nan=False, allow_infinity=False
        ),
        min_size=1,
        max_size=100,
    ),
    st.floats(allow_nan=False, allow_infinity=False, min_value=1, max_value=10**9),
)
def test_p_operations(a, b):
    p = Prg()
    p.i = I(size=len(a))
    p.a = P(p.i, _=a)
    p.b = P(p.i, _=b)

    # Sanity check
    assert len(a) == len(p.a._) == len(p.b._)

    # Addition
    p.add = p.a + p.b
    assert all(
        math.isclose(v, a[i] + b, rel_tol=1e-9, abs_tol=0.0)
        for i, v in enumerate(p.add._)
    )

    # Subtraction
    p.sub = p.a - p.b
    assert all(
        math.isclose(v, a[i] - b, rel_tol=1e-9, abs_tol=0.0)
        for i, v in enumerate(p.sub._)
    )

    # Multiplication
    p.mul = p.a * p.b
    assert all(
        math.isclose(v, a[i] * b, rel_tol=1e-9, abs_tol=0.0)
        for i, v in enumerate(p.mul._)
    )

    # Division (only if no NaNs in a)
    if not any(math.isnan(x) for x in a):
        p.div = p.a / p.b
        assert all(
            math.isclose(v, a[i] / b, rel_tol=1e-9, abs_tol=0.0)
            for i, v in enumerate(p.div._)
        )


test_p_operations()
