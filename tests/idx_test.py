import pytest
from src.gana.block.program import Prg
from src.gana.sets.index import I


@pytest.fixture
def repeat_elem():
    """Element is repeated"""
    _p = Prg()
    _p.i0 = I('a', 'b', mutable=True)
    # a is repeated
    _p.i1 = I('d', 'a')
    # i0 is mutated
    _p.i0 = I('d', 'a', 'c')
    return _p


def test_repeat_elem(repeat_elem):
    """Test that repeated elements in index sets are handled correctly."""
    assert repeat_elem.i0._ == [
        repeat_elem.a,
        repeat_elem.b,
        repeat_elem.d,
        repeat_elem.c,
    ]
    assert repeat_elem.i1._ == [repeat_elem.d, repeat_elem.a]
    assert repeat_elem.a.parent == [repeat_elem.i0, repeat_elem.i1]
    assert repeat_elem.b.parent == [repeat_elem.i0]
    assert repeat_elem.d.parent == [repeat_elem.i1, repeat_elem.i0]


@pytest.fixture
def solarsys():
    _p = Prg()
    _p.giants = I('jupiter', 'saturn', 'uranus', 'neptune')
    _p.rocky = I('mercury', 'venus', 'earth', 'mars')
    _p.gasgiants = I('jupiter', 'saturn')
    _p.minor = I('ceres', 'pluto', 'makemake', 'eris')
    _p.asteroid = I('ceres')
    _p.former = I('pluto')
    _p.voyager = I('saturn', 'neptune', 'uranus', 'titan', 'earth', 'jupiter')
    _p.icegiants = _p.giants - _p.gasgiants
    _p.hasheart = _p.minor & _p.former
    _p.planets = _p.gasgiants | _p.icegiants | _p.rocky
    _p.dense = _p.voyager ^ _p.giants
    _p.i = I('a', 'b', 'c')
    _p.j = I('p')
    _p.k = I(size=2)
    # _p.l = _p.i * _p.j * _p.k
    return _p


def test_idx_operations(solarsys):

    assert solarsys.jupiter.parent == [
        solarsys.giants,
        solarsys.gasgiants,
        solarsys.voyager,
        solarsys.planets,
    ]
    assert solarsys.saturn.parent == [
        solarsys.giants,
        solarsys.gasgiants,
        solarsys.voyager,
        solarsys.planets,
    ]
    assert solarsys.uranus.parent == [
        solarsys.giants,
        solarsys.voyager,
        solarsys.icegiants,
        solarsys.planets,
    ]
    assert solarsys.neptune.parent == [
        solarsys.giants,
        solarsys.voyager,
        solarsys.icegiants,
        solarsys.planets,
    ]
    assert solarsys.mercury.parent == [solarsys.rocky, solarsys.planets]
    assert solarsys.venus.parent == [solarsys.rocky, solarsys.planets]
    assert solarsys.earth.parent == [
        solarsys.rocky,
        solarsys.voyager,
        solarsys.planets,
        solarsys.dense,
    ]
    assert solarsys.mars.parent == [solarsys.rocky, solarsys.planets]
    assert solarsys.ceres.parent == [solarsys.minor, solarsys.asteroid]
    assert solarsys.eris.parent == [solarsys.minor]
    assert solarsys.pluto.parent == [solarsys.minor, solarsys.former, solarsys.hasheart]
    assert solarsys.jupiter.pos == [0, 0, 5, 0]
    assert solarsys.saturn.pos == [1, 1, 0, 1]
    assert solarsys.uranus.pos == [2, 2, 0, 2]
    assert solarsys.neptune.pos == [3, 1, 1, 3]
    assert solarsys.mercury.pos == [0, 4]
    assert solarsys.venus.pos == [1, 5]
    assert solarsys.earth.pos == [2, 4, 6, 1]
    assert solarsys.mars.pos == [3, 7]
    assert solarsys.ceres.pos == [0, 0]
    assert solarsys.eris.pos == [3]
    assert solarsys.pluto.pos == [1, 0, 0]

    assert solarsys.jupiter.n == 0
    assert solarsys.saturn.n == 1
    assert solarsys.uranus.n == 2
    assert solarsys.neptune.n == 3
    assert solarsys.mercury.n == 4
    assert solarsys.venus.n == 5
    assert solarsys.earth.n == 6
    assert solarsys.mars.n == 7
    assert solarsys.ceres.n == 8
    assert solarsys.eris.n == 11
    assert solarsys.pluto.n == 9

    assert solarsys.giants._ == [
        solarsys.jupiter,
        solarsys.saturn,
        solarsys.uranus,
        solarsys.neptune,
    ]
    assert solarsys.rocky._ == [
        solarsys.mercury,
        solarsys.venus,
        solarsys.earth,
        solarsys.mars,
    ]
    assert solarsys.gasgiants._ == [solarsys.jupiter, solarsys.saturn]
    assert solarsys.minor._ == [
        solarsys.ceres,
        solarsys.pluto,
        solarsys.makemake,
        solarsys.eris,
    ]
    assert solarsys.asteroid._ == [solarsys.ceres]
    assert solarsys.former._ == [solarsys.pluto]
    assert solarsys.voyager._ == [
        solarsys.saturn,
        solarsys.neptune,
        solarsys.uranus,
        solarsys.titan,
        solarsys.earth,
        solarsys.jupiter,
    ]
    assert solarsys.icegiants._ == [solarsys.uranus, solarsys.neptune]
    assert solarsys.hasheart._ == [solarsys.pluto]
    assert solarsys.planets._ == [
        solarsys.jupiter,
        solarsys.saturn,
        solarsys.uranus,
        solarsys.neptune,
        solarsys.mercury,
        solarsys.venus,
        solarsys.earth,
        solarsys.mars,
    ]
    assert solarsys.dense._ == [solarsys.titan, solarsys.earth]
    # assert solarsys.l._ == [
    #     (solarsys.a, solarsys.solarsys, solarsys.k[0]),
    #     (solarsys.a, solarsys.solarsys, solarsys.k[1]),
    #     (solarsys.b, solarsys.solarsys, solarsys.k[0]),
    #     (solarsys.b, solarsys.solarsys, solarsys.k[1]),
    #     (solarsys.c, solarsys.solarsys, solarsys.k[0]),
    #     (solarsys.c, solarsys.solarsys, solarsys.k[1]),
    # ]
    assert solarsys.index_sets == [
        solarsys.giants,
        solarsys.rocky,
        solarsys.gasgiants,
        solarsys.minor,
        solarsys.asteroid,
        solarsys.former,
        solarsys.voyager,
        solarsys.icegiants,
        solarsys.hasheart,
        solarsys.planets,
        solarsys.dense,
        solarsys.i,
        solarsys.j,
        solarsys.k,
        # solarsys.l,
    ]
    assert solarsys.indices == [
        solarsys.jupiter,
        solarsys.saturn,
        solarsys.uranus,
        solarsys.neptune,
        solarsys.mercury,
        solarsys.venus,
        solarsys.earth,
        solarsys.mars,
        solarsys.ceres,
        solarsys.pluto,
        solarsys.makemake,
        solarsys.eris,
        solarsys.titan,
        solarsys.a,
        solarsys.b,
        solarsys.c,
        solarsys.p,
    ]
