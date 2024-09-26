# """Operation tests
# """

# import pytest

# from gana.value.m import M
# from gana.value.z import Z
# from src.gana.element.s import S
# from src.gana.element.v import V
# from src.gana.element.x import X
# from src.gana.element.p import P
# from src.gana.relational.f import F
# from src.gana.element.t import T
# from src.gana.relational.c import C
# from src.gana.relational.o import O
# from src.gana.block.prg import Prg

# # Naming
# # x0 not defined with any input
# # x_ negative
# # px assigned to a program


# @pytest.fixture
# def prg():
#     """program"""
#     return Prg()


# @pytest.fixture
# def m():
#     """big M"""
#     return M()


# @pytest.fixture
# def m_():
#     """negative big M"""
#     return M(pos=False)


# @pytest.fixture
# def z():
#     """small m"""
#     return Z()


# @pytest.fixture
# def z_():
#     """negative small m"""
#     return Z(pos=False)


# @pytest.fixture
# def s0():
#     """empty set"""
#     return S()


# @pytest.fixture
# def s():
#     """set"""
#     return S('1', 4, 2.0)


# @pytest.fixture
# def ps(prg):
#     """Program set"""
#     prg.s = S('a', 'b', 'c')
#     return prg.s


# @pytest.fixture
# def v0():
#     """empty variable"""
#     return V()


# @pytest.fixture
# def v(s):
#     """variable"""
#     return V(s)


# @pytest.fixture
# def pv(prg, s):
#     """Program variable"""
#     prg.v = V(s)
#     return prg.v


# @pytest.fixture
# def x0():
#     """empty integer variable"""
#     return X()


# @pytest.fixture
# def x(s):
#     """integer variable"""
#     return X(s)


# @pytest.fixture
# def px(prg, s):
#     """Program integer variable"""
#     prg.x = X(s)
#     return prg.x


# @pytest.fixture
# def p0():
#     """parameter"""
#     return P(_=4)


# @pytest.fixture
# def ps0():
#     """parameter set"""
#     return P(_=[0, 1, 3, 4, 5, 6])


# @pytest.fixture
# def pp(prg):
#     """Program parameter"""
#     prg.p = P(_=4)
#     return prg.p


# @pytest.fixture
# def pps(prg, s):
#     """Program parameter set"""
#     prg.p = P(s, _=[0, 3, 4])
#     return prg.p
