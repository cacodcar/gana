"""Operators"""

from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ..sets.variable import V
    from ..sets.function import F
    from ..sets.index import I


def sigma(vs: V, hold: I, over: I) -> None:
    """Summation"""

    func: F = sum(vs(*hold, idx) for idx in over)
    func.issum = (vs, hold, over)
    return func


# def pi(vs: V, hold: I, over: I) -> None:
#     """Product"""

#     func: F = prod(vs(*hold, idx) for idx in over)
#     func.isprod = True
#     return func
