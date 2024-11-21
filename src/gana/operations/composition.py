"""Function Compositions"""

from ..elements.function import Func
from ..elements.objective import Obj


def inf(func: Func) -> Func:
    """Minimize the function"""
    return Obj(func=func)


def sup(func: Func) -> Func:
    """Maximize the function"""
    return Obj(func=-func)
