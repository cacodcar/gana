import pytest
from src.gana.block.program import Prg
from src.gana.operators.composition import inf
from src.gana.sets.index import I
from src.gana.sets.variable import V
from src.gana.sets.theta import T
from numpy import allclose, array


@pytest.fixture
def mplp():
    p = Prg()
    p.i = I(size=4)
    p.j = I(size=2)
    p.x = V(p.i)
    p.t = T(p.j, _=[(0, 1000), (0, 1000)])

    p.c0 = p.x[0] + p.x[1] <= 350
    p.c1 = p.x[2] + p.x[3] <= 600
    p.c2 = p.x[0] + p.x[2] >= p.t[0]
    p.c3 = p.x[1] + p.x[3] >= p.t[1]
    p.f = inf(178 * p.x[0] + 187 * p.x[1] + 187 * p.x[2] + 151 * p.x[3])
    p.solve()

    return p


def test_mplp(mplp):
    assert len(mplp.solutions[0]) == 3
    assert allclose(
        mplp.solutions[0].critical_regions[0].A,
        array(
            [
                [4.55111174e-16, -9.58101146e-17],
                [-1.08095644e-16, 2.63420819e-16],
                [1.00000000e00, 2.71726164e-17],
                [-4.43739537e-16, 1.00000000e00],
            ]
        ),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[1].A,
        array(
            [
                [1.00000000e00, 2.09065079e-16],
                [1.08808090e-16, 1.00000000e00],
                [-2.11921834e-16, 2.07793336e-17],
                [-2.85118428e-17, -1.47477738e-16],
            ]
        ),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[2].A,
        array(
            [
                [1.00000000e00, 0.00000000e00],
                [0.00000000e00, 1.45579955e-18],
                [6.05443585e-17, 0.00000000e00],
                [0.00000000e00, 1.00000000e00],
            ]
        ),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[0].b,
        array([[3.50000000e02], [3.02929788e-14], [-3.50000000e02], [1.05252933e-13]]),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[1].b,
        array([[8.57310942e-14], [-6.00000000e02], [-8.21908157e-14], [6.00000000e02]]),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[2].b,
        array([[0.0], [0.0], [0.0], [0.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[0].C,
        array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[1].C,
        array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[2].C,
        array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[0].d,
        array([[12.72792206], [323.89350102], [261.53967194], [45.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[1].d,
        array([[50.91168825], [308.30504375], [323.89350102], [45.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[2].d,
        array([[308.30504375], [261.53967194], [36.0], [9.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[0].E,
        array(
            [
                [7.07106781e-01, 7.07106781e-01],
                [-1.00000000e00, -2.71726164e-17],
                [4.43739537e-16, -1.00000000e00],
                [0.00000000e00, -1.00000000e00],
            ]
        ),
        rtol=1e-9,
        atol=1e-12,
    )
    assert allclose(
        mplp.solutions[0].critical_regions[1].E,
        array(
            [
                [7.07106781e-01, 7.07106781e-01],
                [-1.00000000e00, -2.09065079e-16],
                [-1.08808090e-16, -1.00000000e00],
                [-1.00000000e00, 0.00000000e00],
            ]
        ),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[2].E,
        array(
            [
                [1.00000000e00, 1.45579955e-18],
                [6.05443585e-17, 1.00000000e00],
                [-1.00000000e00, 0.00000000e00],
                [0.00000000e00, -1.00000000e00],
            ]
        ),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[0].f,
        array([[6.71751442e02], [-3.50000000e02], [1.05252933e-13], [0.00000000e00]]),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[1].f,
        array([[6.71751442e02], [8.57310942e-14], [-6.00000000e02], [0.00000000e00]]),
        rtol=1e-9,
        atol=1e-12,
    )

    assert allclose(
        mplp.solutions[0].critical_regions[2].f,
        array([[350.0], [600.0], [0.0], [0.0]]),
        rtol=1e-9,
        atol=1e-12,
    )
