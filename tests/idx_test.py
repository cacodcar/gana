import pytest
from src.gana.block.program import Prg
from src.gana.elements.idx import X
from src.gana.sets.index import I


@pytest.fixture
def p():
    p_ = Prg()
    p_.giants = I('jupiter', 'saturn', 'uranus', 'neptune')
    p_.rocky = I('mercury', 'venus', 'earth', 'mars')
    p_.gasgiants = I('jupiter', 'saturn')
    p_.minor = I('ceres', 'pluto', 'makemake', 'eris')
    p_.asteroid = I('ceres')
    p_.former = I('pluto')
    p_.voyager = I('saturn', 'neptune', 'uranus', 'titan', 'earth', 'jupiter')
    p_.icegiants = p_.giants - p_.gasgiants
    p_.hasheart = p_.minor & p_.former
    p_.planets = p_.gasgiants | p_.icegiants | p_.rocky
    p_.dense = p_.voyager ^ p_.giants
    p_.i = I('a', 'b', 'c')
    p_.j = I('p')
    p_.k = I(size=2)
    p_.l = p_.i * p_.j * p_.k
    return p_


def test_idx(p):

    X('a', 'I', 0)
    X(2, 'I', 0)

    assert p.jupiter == 'jupiter'
    assert p.jupiter.parent == [p.giants, p.gasgiants, p.voyager, p.planets]
    assert p.saturn.parent == [p.giants, p.gasgiants, p.voyager, p.planets]
    assert p.uranus.parent == [p.giants, p.voyager, p.icegiants, p.planets]
    assert p.neptune.parent == [p.giants, p.voyager, p.icegiants, p.planets]
    assert p.mercury.parent == [p.rocky, p.planets]
    assert p.venus.parent == [p.rocky, p.planets]
    assert p.earth.parent == [p.rocky, p.voyager, p.planets, p.dense]
    assert p.mars.parent == [p.rocky, p.planets]
    assert p.ceres.parent == [p.minor, p.asteroid]
    assert p.eris.parent == [p.minor]
    assert p.pluto.parent == [p.minor, p.former, p.hasheart]
    assert p.jupiter.pos == [0, 0, 5, 0]
    assert p.saturn.pos == [1, 1, 0, 1]
    assert p.uranus.pos == [2, 2, 0, 2]
    assert p.neptune.pos == [3, 1, 1, 3]
    assert p.mercury.pos == [0, 4]
    assert p.venus.pos == [1, 5]
    assert p.earth.pos == [2, 4, 6, 1]
    assert p.mars.pos == [3, 7]
    assert p.ceres.pos == [0, 0]
    assert p.eris.pos == [3]
    assert p.pluto.pos == [1, 0, 0]

    assert p.jupiter.n == 0
    assert p.saturn.n == 1
    assert p.uranus.n == 2
    assert p.neptune.n == 3
    assert p.mercury.n == 4
    assert p.venus.n == 5
    assert p.earth.n == 6
    assert p.mars.n == 7
    assert p.ceres.n == 8
    assert p.eris.n == 11
    assert p.pluto.n == 9

    assert p.giants._ == [p.jupiter, p.saturn, p.uranus, p.neptune]
    assert p.rocky._ == [p.mercury, p.venus, p.earth, p.mars]
    assert p.gasgiants._ == [p.jupiter, p.saturn]
    assert p.minor._ == [p.ceres, p.pluto, p.makemake, p.eris]
    assert p.asteroid._ == [p.ceres]
    assert p.former._ == [p.pluto]
    assert p.voyager._ == [p.saturn, p.neptune, p.uranus, p.titan, p.earth, p.jupiter]
    assert p.icegiants._ == [p.uranus, p.neptune]
    assert p.hasheart._ == [p.pluto]
    assert p.planets._ == [
        p.jupiter,
        p.saturn,
        p.uranus,
        p.neptune,
        p.mercury,
        p.venus,
        p.earth,
        p.mars,
    ]
    assert p.dense._ == [p.titan, p.earth]
    assert p.l._ == [
        (p.a, p.p, p.k[0]),
        (p.a, p.p, p.k[1]),
        (p.b, p.p, p.k[0]),
        (p.b, p.p, p.k[1]),
        (p.c, p.p, p.k[0]),
        (p.c, p.p, p.k[1]),
    ]
    assert p.sets.index == [
        p.giants,
        p.rocky,
        p.gasgiants,
        p.minor,
        p.asteroid,
        p.former,
        p.voyager,
        p.icegiants,
        p.hasheart,
        p.planets,
        p.dense,
        p.i,
        p.j,
        p.k,
        p.l,
    ]
    assert p.indices == [
        p.jupiter,
        p.saturn,
        p.uranus,
        p.neptune,
        p.mercury,
        p.venus,
        p.earth,
        p.mars,
        p.ceres,
        p.pluto,
        p.makemake,
        p.eris,
        p.titan,
        p.a,
        p.b,
        p.c,
        p.p,
    ]
