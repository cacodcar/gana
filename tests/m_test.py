import pytest

from src.gana.value.m import M


@pytest.fixture()
def m():
    return M()


def test_m(m):
    assert (m > 1000) is True
    assert (-m < 1000) is True
