"""Function Compositions"""

from ..elements.func import Func
from ..elements.obj import Obj


def inf(func: Func) -> Func:
    """Minimize the function"""
    return Obj(func=func)


def sup(func: Func) -> Func:
    """Maximize the function"""
    return Obj(func=-func)




