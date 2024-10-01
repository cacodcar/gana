import pytest

from gana.value.bigm import M
from gana.value.zero import Z


@pytest.fixture
def m():
    return M()


@pytest.fixture
def z():
    return Z()


def test_m(m):
    assert (m > 1000) is True
    assert (-m < 1000) is True
    assert (m + 1000) == m
    assert (1000 + m) == m
    assert (1000 - m) == -m
    assert (m - 1000) == m
    assert (m * 1000) == m
    assert (1000 * m) == m
    assert (m / 1000) == m
    assert (1000 / m) == 0
    with pytest.raises(ValueError):
        M(-1000)


def test_z(z):
    assert (z > 1000) is False
    assert (-z < 1000) is True
    assert (z + 1000) == 1000
    assert (1000 + z) == 1000
    assert (1000 - z) == 1000
    assert (z - 1000) == -1000
    assert (z * 1000) == z
    assert (1000 * z) == z
    assert (z / 1000) == z
    with pytest.raises(ValueError):
        1000 / z
    with pytest.raises(ValueError):
        Z(-1000)
