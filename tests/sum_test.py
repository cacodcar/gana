import pytest
from src.gana.block.program import Prg
from src.gana.operators.sigma import sigma
from src.gana.sets.index import I
from src.gana.sets.variable import V


@pytest.fixture
def p():
    _p = Prg()
    _p._p = I(size=5)
    _p.q = I(size=5)
    _p.r = I(size=5)
    _p.v = V(_p._p, _p.q, _p.r)
    _p.w = V(_p._p)

    # starting index
    _p.f1 = sigma(_p.v, _p._p)
    # middle index
    _p.f2 = sigma(_p.v, _p.q)
    # last index
    _p.f3 = sigma(_p.v, _p.r)
    # with splice
    _p.f4 = sigma(_p.v(_p._p, _p.q[0:3], _p.r), _p.r)
    _p.f5 = sigma(_p.w, _p._p)
    return _p


def test_sigma(p):
    assert [[j[n] for j in p.f1.variables] for n in range(len(p.f1))] == [
        [p.v[0], p.v[25], p.v[50], p.v[75], p.v[100]],
        [p.v[1], p.v[26], p.v[51], p.v[76], p.v[101]],
        [p.v[2], p.v[27], p.v[52], p.v[77], p.v[102]],
        [p.v[3], p.v[28], p.v[53], p.v[78], p.v[103]],
        [p.v[4], p.v[29], p.v[54], p.v[79], p.v[104]],
        [p.v[5], p.v[30], p.v[55], p.v[80], p.v[105]],
        [p.v[6], p.v[31], p.v[56], p.v[81], p.v[106]],
        [p.v[7], p.v[32], p.v[57], p.v[82], p.v[107]],
        [p.v[8], p.v[33], p.v[58], p.v[83], p.v[108]],
        [p.v[9], p.v[34], p.v[59], p.v[84], p.v[109]],
        [p.v[10], p.v[35], p.v[60], p.v[85], p.v[110]],
        [p.v[11], p.v[36], p.v[61], p.v[86], p.v[111]],
        [p.v[12], p.v[37], p.v[62], p.v[87], p.v[112]],
        [p.v[13], p.v[38], p.v[63], p.v[88], p.v[113]],
        [p.v[14], p.v[39], p.v[64], p.v[89], p.v[114]],
        [p.v[15], p.v[40], p.v[65], p.v[90], p.v[115]],
        [p.v[16], p.v[41], p.v[66], p.v[91], p.v[116]],
        [p.v[17], p.v[42], p.v[67], p.v[92], p.v[117]],
        [p.v[18], p.v[43], p.v[68], p.v[93], p.v[118]],
        [p.v[19], p.v[44], p.v[69], p.v[94], p.v[119]],
        [p.v[20], p.v[45], p.v[70], p.v[95], p.v[120]],
        [p.v[21], p.v[46], p.v[71], p.v[96], p.v[121]],
        [p.v[22], p.v[47], p.v[72], p.v[97], p.v[122]],
        [p.v[23], p.v[48], p.v[73], p.v[98], p.v[123]],
        [p.v[24], p.v[49], p.v[74], p.v[99], p.v[124]],
    ]
    assert [[j[n] for j in p.f2.variables] for n in range(len(p.f2))] == [
        [p.v[0], p.v[5], p.v[10], p.v[15], p.v[20]],
        [p.v[1], p.v[6], p.v[11], p.v[16], p.v[21]],
        [p.v[2], p.v[7], p.v[12], p.v[17], p.v[22]],
        [p.v[3], p.v[8], p.v[13], p.v[18], p.v[23]],
        [p.v[4], p.v[9], p.v[14], p.v[19], p.v[24]],
        [p.v[25], p.v[30], p.v[35], p.v[40], p.v[45]],
        [p.v[26], p.v[31], p.v[36], p.v[41], p.v[46]],
        [p.v[27], p.v[32], p.v[37], p.v[42], p.v[47]],
        [p.v[28], p.v[33], p.v[38], p.v[43], p.v[48]],
        [p.v[29], p.v[34], p.v[39], p.v[44], p.v[49]],
        [p.v[50], p.v[55], p.v[60], p.v[65], p.v[70]],
        [p.v[51], p.v[56], p.v[61], p.v[66], p.v[71]],
        [p.v[52], p.v[57], p.v[62], p.v[67], p.v[72]],
        [p.v[53], p.v[58], p.v[63], p.v[68], p.v[73]],
        [p.v[54], p.v[59], p.v[64], p.v[69], p.v[74]],
        [p.v[75], p.v[80], p.v[85], p.v[90], p.v[95]],
        [p.v[76], p.v[81], p.v[86], p.v[91], p.v[96]],
        [p.v[77], p.v[82], p.v[87], p.v[92], p.v[97]],
        [p.v[78], p.v[83], p.v[88], p.v[93], p.v[98]],
        [p.v[79], p.v[84], p.v[89], p.v[94], p.v[99]],
        [p.v[100], p.v[105], p.v[110], p.v[115], p.v[120]],
        [p.v[101], p.v[106], p.v[111], p.v[116], p.v[121]],
        [p.v[102], p.v[107], p.v[112], p.v[117], p.v[122]],
        [p.v[103], p.v[108], p.v[113], p.v[118], p.v[123]],
        [p.v[104], p.v[109], p.v[114], p.v[119], p.v[124]],
    ]
    assert [[j[n] for j in p.f3.variables] for n in range(len(p.f3))] == [
        [p.v[0], p.v[1], p.v[2], p.v[3], p.v[4]],
        [p.v[5], p.v[6], p.v[7], p.v[8], p.v[9]],
        [p.v[10], p.v[11], p.v[12], p.v[13], p.v[14]],
        [p.v[15], p.v[16], p.v[17], p.v[18], p.v[19]],
        [p.v[20], p.v[21], p.v[22], p.v[23], p.v[24]],
        [p.v[25], p.v[26], p.v[27], p.v[28], p.v[29]],
        [p.v[30], p.v[31], p.v[32], p.v[33], p.v[34]],
        [p.v[35], p.v[36], p.v[37], p.v[38], p.v[39]],
        [p.v[40], p.v[41], p.v[42], p.v[43], p.v[44]],
        [p.v[45], p.v[46], p.v[47], p.v[48], p.v[49]],
        [p.v[50], p.v[51], p.v[52], p.v[53], p.v[54]],
        [p.v[55], p.v[56], p.v[57], p.v[58], p.v[59]],
        [p.v[60], p.v[61], p.v[62], p.v[63], p.v[64]],
        [p.v[65], p.v[66], p.v[67], p.v[68], p.v[69]],
        [p.v[70], p.v[71], p.v[72], p.v[73], p.v[74]],
        [p.v[75], p.v[76], p.v[77], p.v[78], p.v[79]],
        [p.v[80], p.v[81], p.v[82], p.v[83], p.v[84]],
        [p.v[85], p.v[86], p.v[87], p.v[88], p.v[89]],
        [p.v[90], p.v[91], p.v[92], p.v[93], p.v[94]],
        [p.v[95], p.v[96], p.v[97], p.v[98], p.v[99]],
        [p.v[100], p.v[101], p.v[102], p.v[103], p.v[104]],
        [p.v[105], p.v[106], p.v[107], p.v[108], p.v[109]],
        [p.v[110], p.v[111], p.v[112], p.v[113], p.v[114]],
        [p.v[115], p.v[116], p.v[117], p.v[118], p.v[119]],
        [p.v[120], p.v[121], p.v[122], p.v[123], p.v[124]],
    ]
    assert [[j[n] for j in p.f4.variables] for n in range(len(p.f4))] == [
        [p.v[0], p.v[1], p.v[2], p.v[3], p.v[4]],
        [p.v[5], p.v[6], p.v[7], p.v[8], p.v[9]],
        [p.v[10], p.v[11], p.v[12], p.v[13], p.v[14]],
        [p.v[25], p.v[26], p.v[27], p.v[28], p.v[29]],
        [p.v[30], p.v[31], p.v[32], p.v[33], p.v[34]],
        [p.v[35], p.v[36], p.v[37], p.v[38], p.v[39]],
        [p.v[50], p.v[51], p.v[52], p.v[53], p.v[54]],
        [p.v[55], p.v[56], p.v[57], p.v[58], p.v[59]],
        [p.v[60], p.v[61], p.v[62], p.v[63], p.v[64]],
        [p.v[75], p.v[76], p.v[77], p.v[78], p.v[79]],
        [p.v[80], p.v[81], p.v[82], p.v[83], p.v[84]],
        [p.v[85], p.v[86], p.v[87], p.v[88], p.v[89]],
        [p.v[100], p.v[101], p.v[102], p.v[103], p.v[104]],
        [p.v[105], p.v[106], p.v[107], p.v[108], p.v[109]],
        [p.v[110], p.v[111], p.v[112], p.v[113], p.v[114]],
    ]
    assert [[j[n] for j in p.f5.variables] for n in range(len(p.f5))] == [
        [p.w[0], p.w[1], p.w[2], p.w[3], p.w[4]]
    ]
