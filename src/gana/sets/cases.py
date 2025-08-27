"""Special Cases"""

from enum import Enum


class Elem(Enum):
    """Type of function"""

    # if element is a variable
    V = 'variable'
    # if element is a parameter
    P = 'parameter'
    # if element is a theta
    T = 'theta'
    # if element is a function
    F = 'function'


class FCase(Enum):
    """function cases"""

    # Negative variable (-1*v)
    NEGVAR = 'negative_variable'
    # sum of variables over one index element v0 + v1 + v2 + ... + vn
    SUM = 'summation'
    # Negative sum, - (v0 + v1 + v2 + ... + vn)
    NEGSUM = 'negative_summation'

    # Variable, never used to describe a function
    # rather a variable, is always a special case
    # of a function that is just a variable
    VAR = 'variable'

    # once changed, the case becomes
    FVAR = 'variable_as_function'


class PCase(Enum):
    """parameter cases"""

    # just a number, stretched into an array
    NUM = 'number'
    # just a negative number, stretched into an array
    NEGNUM = 'negative_number'
    # zero
    ZERO = 'zero'
    # set of numbers
    SET = 'set'
    # negated set
    NEGSET = 'negative_set'


class ICase(Enum):
    """index cases"""

    # DUMMY INDEX
    DUMMY = 'dummy_index'
    # SELF CONTAINED INDEX
    SELF = 'self_contained_index'
