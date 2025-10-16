"""Birthers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .cases import PCase
from .index import I

if TYPE_CHECKING:
    from .parameter import P
    from .theta import T


def make_P(
    inp: list[float | int] | float | int,
    index: Optional[I] = None,
) -> P:
    """
    Make input into a parameter set (P)

    :param inp: Input to be converted to P
    :type inp: list[float | int] | float | int
    :param index: Index for the parameter set. Defaults to None.
    :type index: I, optional

    :returns: Parameter set (P)
    :rtype: P
    """
    from .parameter import P

    # index is only passed when
    # a numeric type is being stretched
    if index:
        if inp > 0:
            case = PCase.NUM
        elif inp < 0:
            case = PCase.NEGNUM
        else:
            case = PCase.ZERO

        # if number is passed
        # give it the same index as self
        # the values will be stretched at initialization

        p = P(*index, _=inp)
        # set the special case
        p.case = case
        return p

    # if a list is passed
    # the parameter will make a dummy index to meet the size
    p = P(_=inp)
    return p


def make_T(
    inp: tuple[int | float] | list[tuple[int | float]],
    index: Optional[I] = None,
) -> T:
    """
    Make input into a theta set (T)

    :param inp: Input to be converted to T
    :type inp: tuple[int | float] | list[tuple[int | float]]
    :param index: Index for the theta set. Defaults to None.
    :type index: I, optional

    :returns: Theta set (T)
    :rtype: T
    """

    from .theta import T

    # index is only passed when
    # a tuple is being stretched

    if index:
        t = T(*index, _=inp)
        return t

    # if a list is passed
    # the theta will make a dummy index to meet the size
    t = T(_=inp)
    return t
