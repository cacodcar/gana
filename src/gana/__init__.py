"""A barebones mathematical programming package"""

from .block.program import Prg
from .operators.composition import inf, sup
from .operators.sigma import sigma
from .sets.index import I
from .sets.parameter import P
from .sets.theta import T
from .sets.variable import V

__all__ = ["I", "P", "Prg", "T", "V", "inf", "sigma", "sup"]
__version__ = "1.1.0"
