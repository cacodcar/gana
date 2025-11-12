"""A barebones mathematical programming package"""

from .block.program import Prg
from .operators.composition import inf, sup
from .operators.sigma import sigma
from .sets.index import I
from .sets.parameter import P
from .sets.theta import T
from .sets.variable import V

__all__ = ["V", "P", "I", "T", "Prg", "inf", "sup", "sigma"]
__version__ = "1.0.9"
